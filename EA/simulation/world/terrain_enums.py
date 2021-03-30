from sims4 import hash_utilimport enum
class TerrainTag(enum.Int):
    INVALID = 0
    BRICK = hash_util.hash32('brick')
    CARPET = hash_util.hash32('carpet')
    CEMENT = hash_util.hash32('cement')
    DEEPSNOW = hash_util.hash32('deepsnow')
    DIRT = hash_util.hash32('dirt')
    GRASS = hash_util.hash32('grass')
    GRAVEL = hash_util.hash32('gravel')
    HARDWOOD = hash_util.hash32('hardwood')
    LEAVES = hash_util.hash32('leaves')
    LINOLEUM = hash_util.hash32('linoleum')
    MARBLE = hash_util.hash32('marble')
    METAL = hash_util.hash32('metal')
    PUDDLE = hash_util.hash32('puddle')
    SAND = hash_util.hash32('sand')
    SNOW = hash_util.hash32('snow')
    STONE = hash_util.hash32('stone')
    WOOD_DECK = hash_util.hash32('wood deck')
