#************************************************************************************************************************************************
#
# Copyright 2017 David Briant
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#************************************************************************************************************************************************

from mm_sim._core import *
from pprint import pprint

sim = Simulator(["AA"])
sim.addMM(MM3("A").setAsset("AA"))
sim.addMM(MM2("B").setAsset("AA"))
sim.addLT(LT1("C").setAsset("AA"))
for i in range(20):
    sim.simRound()
