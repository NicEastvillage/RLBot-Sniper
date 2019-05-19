import math

from RLUtilities.GameInfo import GameInfo
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.utils.game_state_util import *
from rlbot.utils.structures.game_data_struct import GameTickPacket

from RLUtilities.LinearAlgebra import *

SPEED = 2000
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

    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        dt = packet.game_info.seconds_elapsed - self.last_elapsed_seconds
        self.last_elapsed_seconds = packet.game_info.seconds_elapsed
        self.info.read_packet(packet)

        ball_pos = self.info.ball.pos

        if ball_pos[0] == 0 and ball_pos[1] == 0 and packet.game_info.is_kickoff_pause:
            # Kickoff
            self.shoot_time = self.info.time + AIM_DURATION
            self.controls.boost = False

        elif self.state == self.AIMING:

            self.controls.boost = False

            car_state = CarState(Physics(location=to_fb(self.standby_position), velocity=Vector3(0, 0, 0)))
            game_state = GameState(cars={self.index: car_state})
            self.set_game_state(game_state)

            if self.shoot_time < self.info.time:
                self.state = self.FLYING
                self.direction = normalize(ball_pos - self.standby_position)

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


def to_fb(vec: vec3):
    return Vector3(vec[0], vec[1], vec[2])
