from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/wasm/generated_maps.c"


def words_from(path):
    data = (ROOT / path).read_bytes()
    if len(data) % 2:
        raise ValueError(f"{path} has odd byte length")
    return [data[i] | (data[i + 1] << 8) for i in range(0, len(data), 2)]


def array_u16(name, words):
    rows = []
    for i in range(0, len(words), 12):
        rows.append("    " + ", ".join(f"0x{word:04x}" for word in words[i:i + 12]))
    return f"static const u16 {name}[] = {{\n" + ",\n".join(rows) + "\n};\n"


border = words_from("data/layouts/InsideOfTruck/border.bin")
blockdata = words_from("data/layouts/InsideOfTruck/map.bin")

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(
    "#include \"global.h\"\n"
    "#include \"constants/event_bg.h\"\n"
    "#include \"constants/event_object_movement.h\"\n"
    "#include \"constants/event_objects.h\"\n"
    "#include \"constants/layouts.h\"\n"
    "#include \"constants/map_types.h\"\n"
    "#include \"constants/region_map_sections.h\"\n"
    "#include \"constants/songs.h\"\n"
    "#include \"constants/trainer_types.h\"\n"
    "#include \"constants/weather.h\"\n\n"
    "extern const struct Tileset gTileset_General;\n"
    "extern const struct Tileset gTileset_InsideOfTruck;\n\n"
    + array_u16("sInsideOfTruckBorder", border)
    + "\n"
    + array_u16("sInsideOfTruckBlockdata", blockdata)
    + "\n"
    "static const struct MapLayout sInsideOfTruckLayout = {\n"
    "    .width = 5,\n"
    "    .height = 5,\n"
    "    .border = sInsideOfTruckBorder,\n"
    "    .map = sInsideOfTruckBlockdata,\n"
    "    .primaryTileset = &gTileset_General,\n"
    "    .secondaryTileset = &gTileset_InsideOfTruck,\n"
    "};\n\n"
    "static const struct ObjectEventTemplate sInsideOfTruckObjectEvents[] = {\n"
    "    {.localId = 1, .graphicsId = OBJ_EVENT_GFX_MOVING_BOX, .kind = 0, .x = 0, .y = 0, .elevation = 8, .movementType = MOVEMENT_TYPE_FACE_DOWN, .trainerType = TRAINER_TYPE_NONE},\n"
    "    {.localId = 2, .graphicsId = OBJ_EVENT_GFX_MOVING_BOX, .kind = 0, .x = 0, .y = 3, .elevation = 8, .movementType = MOVEMENT_TYPE_FACE_DOWN, .trainerType = TRAINER_TYPE_NONE},\n"
    "    {.localId = 3, .graphicsId = OBJ_EVENT_GFX_MOVING_BOX, .kind = 0, .x = 2, .y = 3, .elevation = 8, .movementType = MOVEMENT_TYPE_FACE_DOWN, .trainerType = TRAINER_TYPE_NONE},\n"
    "};\n\n"
    "static const struct WarpEvent sInsideOfTruckWarps[] = {\n"
    "    {.x = 4, .y = 1, .elevation = 0, .warpId = WARP_ID_DYNAMIC, .mapNum = MAP_NUM(MAP_DYNAMIC), .mapGroup = MAP_GROUP(MAP_DYNAMIC)},\n"
    "    {.x = 4, .y = 2, .elevation = 0, .warpId = WARP_ID_DYNAMIC, .mapNum = MAP_NUM(MAP_DYNAMIC), .mapGroup = MAP_GROUP(MAP_DYNAMIC)},\n"
    "    {.x = 4, .y = 3, .elevation = 0, .warpId = WARP_ID_DYNAMIC, .mapNum = MAP_NUM(MAP_DYNAMIC), .mapGroup = MAP_GROUP(MAP_DYNAMIC)},\n"
    "};\n\n"
    "static const struct MapEvents sInsideOfTruckMapEvents = {\n"
    "    .objectEventCount = ARRAY_COUNT(sInsideOfTruckObjectEvents),\n"
    "    .warpCount = ARRAY_COUNT(sInsideOfTruckWarps),\n"
    "    .coordEventCount = 0,\n"
    "    .bgEventCount = 0,\n"
    "    .objectEvents = sInsideOfTruckObjectEvents,\n"
    "    .warps = sInsideOfTruckWarps,\n"
    "};\n\n"
    "const struct MapHeader InsideOfTruck = {\n"
    "    .mapLayout = &sInsideOfTruckLayout,\n"
    "    .events = &sInsideOfTruckMapEvents,\n"
    "    .mapScripts = NULL,\n"
    "    .connections = NULL,\n"
    "    .music = MUS_NONE,\n"
    "    .mapLayoutId = LAYOUT_INSIDE_OF_TRUCK,\n"
    "    .regionMapSectionId = MAPSEC_INSIDE_OF_TRUCK,\n"
    "    .cave = FALSE,\n"
    "    .weather = WEATHER_NONE,\n"
    "    .mapType = MAP_TYPE_INDOOR,\n"
    "    .allowCycling = FALSE,\n"
    "    .allowEscaping = FALSE,\n"
    "    .allowRunning = FALSE,\n"
    "    .showMapName = FALSE,\n"
    "    .battleType = MAP_BATTLE_SCENE_NORMAL,\n"
    "};\n\n"
    "const struct MapLayout *const gMapLayouts[] = {\n"
    "    [LAYOUT_INSIDE_OF_TRUCK - 1] = &sInsideOfTruckLayout,\n"
    "};\n\n"
    "const struct MapHeader *const gMapGroup_IndoorDynamic[] = {\n"
    "    [MAP_NUM(MAP_INSIDE_OF_TRUCK)] = &InsideOfTruck,\n"
    "};\n\n"
    "const struct MapHeader *const *const gMapGroups[] = {\n"
    "    [MAP_GROUP(MAP_INSIDE_OF_TRUCK)] = gMapGroup_IndoorDynamic,\n"
    "};\n"
)
print(f"wrote {OUT}")
