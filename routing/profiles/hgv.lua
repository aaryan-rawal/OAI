-- OptiFreight India baseline HGV profile for OSRM backend API v4.
-- This is a conservative starting profile, NOT a certified all-vehicle profile.
api_version = 4
Set = require('lib/set')
Sequence = require('lib/sequence')
WayHandlers = require('lib/way_handlers')
Obstacles = require('lib/obstacles')
Relations = require('lib/relations')

function setup()
  return {
    properties = {
      max_speed_for_map_matching = 100/3.6,
      weight_name = 'routability',
      process_call_tagless_node = false,
      u_turn_penalty = 35,
      continue_straight_at_waypoint = true,
      use_turn_restrictions = true,
    },
    default_mode = mode.driving,
    default_speed = 25,
    oneway_handling = true,
    side_road_multiplier = 0.65,
    turn_penalty = 14,
    speed_reduction = 0.75,
    turn_bias = 1.05,
    oncoming_turn_penalty = 5,
    cardinal_directions = false,

    -- Baseline dimensions only. A single OSRM graph cannot dynamically enforce
    -- every truck's dimensions; build separate profiles/graphs for other classes.
    vehicle_height = 3.8,
    vehicle_width = 2.6,
    vehicle_length = 16.5,
    vehicle_weight = 49000,
    vehicle_max_speed = 80,

    barrier_whitelist = Set {'no','entrance','toll_booth','border_control','cattle_grid','sally_port'},
    barrier_penalties = { gate = 120, lift_gate = 120 },
    access_tag_whitelist = Set {'yes','hgv','goods','motor_vehicle','vehicle','permissive','designated'},
    access_tag_blacklist = Set {'no','private','agricultural','forestry','emergency','foot','restricted','military','official','residents','customers','delivery','destination','permit'},
    service_access_tag_blacklist = Set {'private'},
    restricted_access_tag_list = Set {'private','delivery','destination','customers','permit','residents','unknown'},
    access_tags_hierarchy = Sequence {'hgv','goods','motor_vehicle','vehicle','access'},
    service_tag_forbidden = Set {'emergency_access'},
    restrictions = Sequence {'hgv','goods','motor_vehicle','vehicle'},
    classes = Sequence {'toll','motorway','ferry','restricted','tunnel'},
    excludable = Sequence { Set {'toll'}, Set {'motorway'}, Set {'ferry'} },
    avoid = Set {'area','reversible','impassable','hov_lanes','steps','construction','proposed'},

    speeds = Sequence { highway = {
      motorway = 70, motorway_link = 30, trunk = 65, trunk_link = 25,
      primary = 55, primary_link = 22, secondary = 40, secondary_link = 18,
      tertiary = 30, tertiary_link = 15, unclassified = 22,
      residential = 18, living_street = 8, service = 10,
    } },
    service_penalties = { alley = 0.35, parking = 0.35, parking_aisle = 0.35, driveway = 0.25 },
    restricted_highway_whitelist = Set {'motorway','motorway_link','trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','living_street','service'},
    construction_whitelist = Set {'no','widening','minor'},
    route_speeds = { ferry = 5, shuttle_train = 5 },
    bridge_speeds = { movable = 3 },
    surface_speeds = {
      asphalt = 70, concrete = 65, paved = 60, cement = 50, compacted = 35,
      fine_gravel = 25, paving_stones = 20, gravel = 18, unpaved = 12,
      ground = 10, dirt = 8, mud = 4, sand = 4, cobblestone = 10,
    },
    tracktype_speeds = { grade1 = 30, grade2 = 18, grade3 = 10, grade4 = 5, grade5 = 3 },
    smoothness_speeds = { intermediate = 35, bad = 15, very_bad = 7, horrible = 3, very_horrible = 1, impassable = 0 },
    maxspeed_table_default = { urban = 40, rural = 70, trunk = 80, motorway = 80 },
    maxspeed_table = { ['IN:urban'] = 40, ['IN:rural'] = 70, ['IN:trunk'] = 80, ['IN:motorway'] = 80, ['none'] = 80 },
    relation_types = Sequence {'route'},
    highway_turn_classification = {},
    access_turn_classification = {},
  }
end

function process_node(profile, node, result, relations)
  Obstacles.process_node(profile, node)
end

function process_way(profile, way, result, relations)
  local data = {
    highway = way:get_value_by_key('highway'),
    bridge = way:get_value_by_key('bridge'),
    route = way:get_value_by_key('route')
  }
  if (not data.highway or data.highway == '') and (not data.route or data.route == '') then return end
  local handlers = Sequence {
    WayHandlers.default_mode, WayHandlers.blocked_ways, WayHandlers.avoid_ways,
    WayHandlers.handle_height, WayHandlers.handle_width, WayHandlers.handle_length,
    WayHandlers.handle_weight, WayHandlers.access, WayHandlers.oneway,
    WayHandlers.destinations, WayHandlers.ferries, WayHandlers.movables,
    WayHandlers.service, WayHandlers.speed, WayHandlers.maxspeed,
    WayHandlers.surface, WayHandlers.vehicle_speed_cap, WayHandlers.penalties,
    WayHandlers.classes, WayHandlers.turn_lanes, WayHandlers.classification,
    WayHandlers.roundabouts, WayHandlers.startpoint, WayHandlers.driving_side,
    WayHandlers.names, WayHandlers.weights, WayHandlers.way_classification_for_turn
  }
  WayHandlers.run(profile, way, result, data, handlers, relations)
  if profile.cardinal_directions then Relations.process_way_refs(way, relations, result) end
end

function process_turn(profile, turn)
  if turn.is_u_turn then turn.duration = turn.duration + profile.properties.u_turn_penalty end
  if turn.number_of_roads > 2 then turn.duration = turn.duration + profile.turn_penalty end
  turn.weight = turn.duration
end

return { setup = setup, process_way = process_way, process_node = process_node, process_turn = process_turn }
