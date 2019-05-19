import math

from RLUtilities.GameInfo import GameInfo
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

from RLUtilities.LinearAlgebra import *

SPEED = 2500
AIM_DURATION = 1.5


class SniperBot(BaseAgent):
    AIMING = 0
    FLYING = 1

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.controls = SimpleControllerState()
        self.info = GameInfo(self.index, self.team)
        tsign = -1 if self.team == 0 else 1
        self.standby_position = vec3(0, tsign * 5030, 300)
        self.direction = -1 * vec3(0, tsign, 0)
        self.state = self.AIMING
        self.shoot_time = 0
        self.last_pos = self.standby_position
        self.last_elapsed_seconds = 0
        self.last_gtr = 0

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        dt = packet.game_info.seconds_elapsed - self.last_elapsed_seconds
        dt_gtr = packet.game_info.game_time_remaining - self.last_gtr
        self.last_gtr = packet.game_info.game_time_remaining
        self.last_elapsed_seconds = packet.game_info.seconds_elapsed
        self.info.read_packet(packet)

        ball_pos = self.info.ball.pos

        print(packet.game_info.is_kickoff_pause, packet.game_info.is_round_active, dt == 0, packet.game_info.game_time_remaining, dt_gtr, packet.game_info.seconds_elapsed)

        if ball_pos[0] == 0 and ball_pos[1] == 0 and packet.game_info.is_kickoff_pause:
            # Kickoff and pauses
            self.state = self.AIMING
            self.shoot_time = self.info.time + AIM_DURATION
            self.controls.boost = False

        elif self.state == self.AIMING:

            self.controls.boost = False
            ball_pos = self.predicted_ball_pos()
            self.direction = d = normalize(ball_pos - self.standby_position)

            rotation = Rotator(0, math.atan2(d[1], d[0]), 0)
            car_state = CarState(Physics(location=to_fb(self.standby_position),
                                         velocity=Vector3(0, 0, 0),
                                         rotation=rotation,
                                         angular_velocity=Vector3(0, 0, 0)))
            game_state = GameState(cars={self.index: car_state})
            self.set_game_state(game_state)

            self.renderer.begin_rendering()
            self.renderer.draw_rect_3d(ball_pos, 10, 10, True, self.renderer.team_color(), True)
            self.renderer.end_rendering()

            if self.shoot_time < self.info.time:
                self.state = self.FLYING

        elif self.state == self.FLYING:

            vel = self.direction * SPEED
            n_pos = self.last_pos + vel * dt

            car_state = CarState(Physics(location=to_fb(n_pos), velocity=to_fb(vel)))
            game_state = GameState(cars={self.index: car_state})
            self.set_game_state(game_state)

            self.last_pos = n_pos

            if abs(n_pos[0]) > 4080 or abs(n_pos[1]) > 5080 or n_pos[2] < 0 or n_pos[2] > 2020:
                self.state = self.AIMING
                self.shoot_time = self.info.time + AIM_DURATION
                self.last_pos = self.standby_position

        return self.controls

    def predicted_ball_pos(self):
        ball_prediction = self.get_ball_prediction_struct()

        if ball_prediction is not None:
            SLICES_PER_SEC = 60
            SECONDS = 6

            dist = norm(self.info.my_car.pos - self.info.ball.pos)
            time = dist / SPEED
            slice_index = min(max(0, math.floor(SLICES_PER_SEC * time)), SLICES_PER_SEC * SECONDS - 1)
            pos = ball_prediction.slices[slice_index].physics.location
            return vec3(pos.x, pos.y, pos.z)

        return vec3(0, 0, 0)


def to_fb(vec: vec3):
    return Vector3(vec[0], vec[1], vec[2])
