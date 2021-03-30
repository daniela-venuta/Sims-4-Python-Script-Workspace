import enum
class SpawnerType(enum.Int):
    GROUND = 0
    SLOT = 1
    INTERACTION = 2

class SpawnLocation(enum.Int):
    SPAWNER = 0
    PORTAL = 1
