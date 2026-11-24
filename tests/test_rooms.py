import rooms
import pytest
def test_rooms_optional_and_distinct():
    assert rooms.normalize([])==[]
    p=rooms.normalize([{'id':'a','name':'Kitchen','sensors':{'co2':{'entity':'sensor.a','unit':'ppm'}}},{'id':'b','sensors':{'co2':{'entity':'sensor.b','unit':'ppm'}}}])
    assert len(rooms.mappings(p))==2
    assert rooms.co2_config({'mapping':{}},p[1])['mapping']['co2_indoor']['entity']=='sensor.b'
def test_invalid_room_unit():
    with pytest.raises(ValueError):rooms.normalize([{'id':'a','sensors':{'co2':{'entity':'sensor.a','unit':'W'}}}])
