from base_instr import BaseInstr


class SussPA300(BaseInstr):
    def __init__(self, instr_resource, timeout_sec, debug_mode=False):
        self._debug_mode = debug_mode
        super().__init__(instr_resource, timeout_sec, self._debug_mode)
        if self._debug_mode:
            return
        if self.q('*IDN?') != 'Suss MicroTec Test Systems GmbH,ProberBench PC,0,0':
            raise RuntimeError('Failed to connect to SUSS PA300.')
        # self.w('*RST')
        self.check_status()

    # 20,000um = 2cm
    __negative_xyz_micron_limit_from_center = (-20000, -20000, 5200)
    __positive_xyz_micron_limit_from_center = (20000, 20000, 13000)

    def read_xyz(self, coordinate):
        """
        Returns [x, y, z] in micro meter.
         'H': relative to home,'Z': relative to zero, 'C': relative to center.
        :type coordinate: string
        :return: [x, y, z]
        """
        if coordinate not in ('H', 'Z', 'C'):
            raise ValueError("Parameter coordinate must be one of ('H', 'Z', 'C')"
                             "(relative to home, zero, center)")
        # Y: micron.  "0: 0.0 -0.5 -300.08" -> ["0:", "0.0", "-0.5", "-300.08"]
        if self._debug_mode:
            if coordinate == 'H':
                return [-2424.0, -2425.5, -100.0]
            if coordinate == 'Z':
                return [157599.5, 155000.0, 10947.6]
            if coordinate == 'C':
                return [-0.5, 0.0, 10947.6]
        res = self.q('ReadChuckPosition Y {} D'.format(coordinate)).split()
        # -> [0.0, -0.5, -300.08]
        return [float(elem) for elem in res[1:]]

    _velocity = 1

    @property
    def velocity(self):
        return self._velocity

    @velocity.setter
    def velocity(self, value):
        if value <= 0 or 100 < value: raise ValueError('Invalid velocity.')
        self._velocity = value

    def _over_limit_from_center(self, xyz):
        """
        self._over_limit_from_center((10, 10)) --> checks only x and y
        :param xyz:
        :return:
        """
        for (position, n_lim) in zip(xyz, self.__negative_xyz_micron_limit_from_center):
            if position < n_lim:
                return True
        for (position, p_lim) in zip(xyz, self.__positive_xyz_micron_limit_from_center):
            if p_lim < position:
                return True
        return False

    def check_status(self):
        if self._debug_mode:
            return
        # Query example: '0: PA300PS_ 5 1 1 1 0 0 0 0 0'
        stat = self.q('ReadSystemStatus')
        if stat.split(':')[0] != '0':
            raise RuntimeError('Something error in SUSS. (non-zero status code)')
        x, y, z = self.read_xyz('C')
        if self._over_limit_from_center((x, y, z)):
            raise RuntimeError('Over xyz limit.')

    def move_to_xy_from_center(self, x, y):
        if self._over_limit_from_center((x, y)):
            raise RuntimeError('Exceeds xy limit.')
        if self._debug_mode:
            return
        query_response = self.q('ReadChuckStatus')  # example '7 7 0 0 L 1 C 0'
        # if not separation or alignment # TODO implement
        # if not query_response.split()[6] in ('S', 'A'):
        #     raise RuntimeError('Separate or align before!')
        self.q('MoveChuck {} {} C {}'.format(x, y, self._velocity))
        self.check_status()

    def move_to_xy_from_home(self, x, y):
        xy_from_home = self.read_xyz('H')[:2]
        xy_from_center = self.read_xyz('C')[:2]
        self.move_to_xy_from_center(x + xy_from_center[0] - xy_from_home[0], y + xy_from_center[1] - xy_from_home[1])

    def align(self):
        self.q('MoveChuckAlignt {}'.format(self.velocity))
        self.check_status()

    def contact(self):
        self.q('MoveChuckContact {}'.format(self.velocity))
        self.check_status()

    def moveZ(self, z):
        if z < self.__negative_xyz_micron_limit_from_center[2] or self.__positive_xyz_micron_limit_from_center[2] < z:
            raise RuntimeError('Parameter exceeds z limit.')
        self.q('MoveChuckZ {} Z Y {}'.format(z, self.velocity))
        self.check_status()
