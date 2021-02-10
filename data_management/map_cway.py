MAP_CWAY_TO_INT = {
	'Left':   0b0001,
	'Single': 0b0010,
	'Right':  0b0100
}

MAP_INT_TO_CWAY_STRING = {
	0b0001: 'Left',
	0b0010: 'Single',
	0b0100: 'Right'
}

MAP_CWAY_REQUEST_TO_MASK = {
	"L":   0b0001,
	"S":   0b0010,
	"R":   0b0100,
	"LRS": 0b0111,
	"LR":  0b0101,
	"LS":  0b0011,
	"RS":  0b0110,
}
