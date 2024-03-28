# ridesharing-optimization
Ride-sharing optimization formulation based on queuing theory [1].
<div align="center">
    <img src="./img/flow_map.svg" alt="demand flow" width="150">
</div>


### :memo: Problem formulation

- Manhattan is divided into 63 zones.
- Traffic flow of each zone is modeled as an M/M/1 queue.
- Demand and supply of an M/M/1 queue are calculated from average traffic inflows and outflows during four years [2].
- The average traffic inflows and outflows are in `./data` for each time period (weekday morning, weekday lunch, weekday dinner, weekday night, weekend morning, weekend lunch, weekend dinner, weekend night).

### :pushpin: References
[1] Lee, Jungeun and Kim, Sunhwi and Kim, Eunchong and Vo, Cong Phat and Song, Jeonghwan and Jeon, Jeong hwan, Deep Reinforcement Learning-Based Autonomous Ride-Sharing System. Available at SSRN: https://ssrn.com/abstract=4773032 or http://dx.doi.org/10.2139/ssrn.4773032
[2] Donovan, Brian; Work, Dan (2016): New York City Taxi Trip Data (2010-2013). University of Illinois at Urbana-Champaign. https://doi.org/10.13012/J8PN93H8