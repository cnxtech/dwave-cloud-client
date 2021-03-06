# Copyright 2017 D-Wave Systems Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from collections import OrderedDict
from itertools import count
from datetime import datetime

from dwave.cloud.utils import (
    uniform_iterator, uniform_get, strip_head, strip_tail,
    active_qubits, generate_random_ising_problem,
    default_text_input, utcnow, cached)
from dwave.cloud.testing import mock


class TestSimpleUtils(unittest.TestCase):

    def test_uniform_iterator(self):
        items = [('a', 1), ('b', 2)]
        self.assertEqual(list(uniform_iterator(OrderedDict(items))), items)
        self.assertEqual(list(uniform_iterator('ab')), list(enumerate('ab')))

    def test_uniform_get(self):
        d = {0: 0, 1: 1}
        self.assertEqual(uniform_get(d, 0), 0)
        self.assertEqual(uniform_get(d, 2), None)
        self.assertEqual(uniform_get(d, 2, default=0), 0)
        l = [0, 1]
        self.assertEqual(uniform_get(l, 0), 0)
        self.assertEqual(uniform_get(l, 2), None)
        self.assertEqual(uniform_get(l, 2, default=0), 0)

    def test_strip_head(self):
        self.assertEqual(strip_head([0, 0, 1, 2], [0]), [1, 2])
        self.assertEqual(strip_head([1], [0]), [1])
        self.assertEqual(strip_head([1], []), [1])
        self.assertEqual(strip_head([0, 0, 1, 2], [0, 1, 2]), [])

    def test_strip_tail(self):
        self.assertEqual(strip_tail([1, 2, 0, 0], [0]), [1, 2])
        self.assertEqual(strip_tail([1], [0]), [1])
        self.assertEqual(strip_tail([1], []), [1])
        self.assertEqual(strip_tail([0, 0, 1, 2], [0, 1, 2]), [])

    def test_active_qubits_dict(self):
        self.assertEqual(active_qubits({}, {}), set())
        self.assertEqual(active_qubits({0: 0}, {}), {0})
        self.assertEqual(active_qubits({}, {(0, 1): 0}), {0, 1})
        self.assertEqual(active_qubits({2: 0}, {(0, 1): 0}), {0, 1, 2})

    def test_active_qubits_list(self):
        self.assertEqual(active_qubits([], {}), set())
        self.assertEqual(active_qubits([2], {}), {0})
        self.assertEqual(active_qubits([2, 2, 0], {}), {0, 1, 2})
        self.assertEqual(active_qubits([], {(0, 1): 0}), {0, 1})
        self.assertEqual(active_qubits([0, 0], {(0, 2): 0}), {0, 1, 2})

    def test_default_text_input(self):
        val = "value"
        with mock.patch("six.moves.input", side_effect=[val], create=True):
            self.assertEqual(default_text_input("prompt", val), val)
        with mock.patch("six.moves.input", side_effect=[val], create=True):
            self.assertEqual(default_text_input("prompt", val+val), val)

    def test_generate_random_ising_problem(self):
        class MockSolver(object):
            nodes = [0, 1, 3]
            undirected_edges = {(0, 1), (1, 3), (0, 4)}
            properties = dict(h_range=[2, 2], j_range=[-1, -1])
        mock_solver = MockSolver()

        lin, quad = generate_random_ising_problem(mock_solver)

        self.assertDictEqual(lin, {0: 2.0, 1: 2.0, 3: 2.0})
        self.assertDictEqual(quad, {(0, 1): -1.0, (1, 3): -1.0, (0, 4): -1.0})

    def test_generate_random_ising_problem_default_solver_ranges(self):
        class MockSolver(object):
            nodes = [0, 1, 3]
            undirected_edges = {(0, 1), (1, 3), (0, 4)}
            properties = {}
        mock_solver = MockSolver()

        lin, quad = generate_random_ising_problem(mock_solver)

        for q, v in lin.items():
            self.assertTrue(v >= -1 and v <= 1)
        for e, v in quad.items():
            self.assertTrue(v >= -1 and v <= 1)

    def test_generate_random_ising_problem_with_user_constrained_ranges(self):
        class MockSolver(object):
            nodes = [0, 1, 3]
            undirected_edges = {(0, 1), (1, 3), (0, 4)}
            properties = dict(h_range=[2, 2], j_range=[-1, -1])
        mock_solver = MockSolver()

        lin, quad = generate_random_ising_problem(mock_solver, h_range=[0,0], j_range=[1,1])

        self.assertDictEqual(lin, {0: 0.0, 1: 0.0, 3: 0.0})
        self.assertDictEqual(quad, {(0, 1): 1.0, (1, 3): 1.0, (0, 4): 1.0})

    def test_utcnow(self):
        t = utcnow()
        now = datetime.utcnow()
        self.assertEqual(t.utcoffset().total_seconds(), 0.0)
        unaware = t.replace(tzinfo=None)
        self.assertLess((now - unaware).total_seconds(), 1.0)


class TestCachedDecorator(unittest.TestCase):

    def test_args_hashing(self):
        counter = count()

        @cached(maxage=300)
        def f(*a, **b):
            return next(counter)

        with mock.patch('dwave.cloud.utils.epochnow', lambda: 0):
            self.assertEqual(f(), 0)
            self.assertEqual(f(1), 1)
            self.assertEqual(f(1, 2), 2)
            self.assertEqual(f(1), 1)
            self.assertEqual(f(1, refresh_=True), 3)
            self.assertEqual(f(1, 2), 2)

            self.assertEqual(f(a=1, b=2), 4)
            self.assertEqual(f(b=2, a=1), 4)
            self.assertEqual(f(b=2, a=1, refresh_=1), 5)
            self.assertEqual(f(), 0)

            self.assertEqual(f(2), 6)
            self.assertEqual(f(1), 3)

    def test_args_collision(self):
        counter = count()

        @cached(maxage=300)
        def f(*a, **b):
            return next(counter)

        with mock.patch('dwave.cloud.utils.epochnow', lambda: 0):
            # NB: in python2, without hash seed randomization,
            # hash('\0B') == hash('\0\0C')
            self.assertEqual(f(x='\0B'), 0)
            self.assertEqual(f(x='\0\0C'), 1)

    def test_expiry(self):
        counter = count()

        @cached(maxage=300)
        def f(*a, **b):
            return next(counter)

        # populate
        with mock.patch('dwave.cloud.utils.epochnow', lambda: 0):
            self.assertEqual(f(), 0)
            self.assertEqual(f(1), 1)
            self.assertEqual(f(a=1, b=2), 2)

        # verify expiry
        with mock.patch('dwave.cloud.utils.epochnow', lambda: 301):
            self.assertEqual(f(), 3)
            self.assertEqual(f(1), 4)
            self.assertEqual(f(a=1, b=2), 5)

        # verify maxage
        with mock.patch('dwave.cloud.utils.epochnow', lambda: 299):
            self.assertEqual(f(), 3)
            self.assertEqual(f(1), 4)
            self.assertEqual(f(a=1, b=2), 5)

    def test_default_maxage(self):
        counter = count()

        @cached()
        def f(*a, **b):
            return next(counter)

        with mock.patch('dwave.cloud.utils.epochnow', lambda: 0):
            self.assertEqual(f(), 0)
            self.assertEqual(f(), 1)
            self.assertEqual(f(), 2)

    def test_exceptions(self):
        counter = count(0)

        @cached()
        def f():
            # raises ZeroDivisionError only on first call
            # we do not want to cache that!
            return 1.0 / next(counter)

        with mock.patch('dwave.cloud.utils.epochnow', lambda: 0):
            self.assertRaises(ZeroDivisionError, f)
            self.assertEqual(f(), 1)
            self.assertEqual(f(), 0.5)


if __name__ == '__main__':
    unittest.main()
