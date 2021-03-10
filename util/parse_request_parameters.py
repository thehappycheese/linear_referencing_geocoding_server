from dataclasses import dataclass
from typing import Optional, List, Dict

class URL_Parameter_Parse_Exception(Exception):
	def __init__(self, message):
		super().__init__(message)
		self.message = message


@dataclass
class Slice_Request_Args:
	road: str
	slk_from: float
	slk_to: float
	offset: float
	cway: str


ERROR_SUGGEST_CORRECT = "Try /?road=H001&slk_from=6.3&slk_to=7 or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35"
ERROR_SUGGEST_CORRECT_ADVANCED = "Try /?road=H001&slk_from=6.3&slk_to=7&offset=-5&cway=L or /?road=H001,H012&slk_from=6.3,16.4&slk_to=7,17.35&offset=-5,5&cway=L,R"


def parse_request_parameters(request: Dict) -> List[Slice_Request_Args]:
	request = {k: v[0] for k, v in request.items()}
	raw_request_roads: Optional[str] = request.get("road", None)
	try:
		assert raw_request_roads is not None
		request_roads: List[str] = raw_request_roads.split(',')
		for item in request_roads:
			assert len(item) > 2
	except:
		raise URL_Parameter_Parse_Exception(f"error: missing or malformed url parameter 'road={request.get('road', None)}'. {ERROR_SUGGEST_CORRECT}") from None
	
	raw_request_slk_from: Optional[str] = request.get("slk_from", None)
	raw_request_slk_to: Optional[str] = request.get("slk_to", None)
	
	try:
		assert raw_request_slk_from is not None
		assert raw_request_slk_to is not None
	except:
		raise URL_Parameter_Parse_Exception("error: missing url parameters 'slk_from' and/or 'slk_to'. " + ERROR_SUGGEST_CORRECT) from None
	
	try:
		str_request_slk_from: List[str] = raw_request_slk_from.split(',')
		str_request_slk_to: List[str] = raw_request_slk_to.split(',')
		assert len(str_request_slk_from) == len(request_roads)
		assert len(str_request_slk_to) == len(request_roads)
	except:
		raise URL_Parameter_Parse_Exception("error: parameters 'slk_from' and 'slk_to' could not be split into lists the same length as the 'road' parameter list. " + ERROR_SUGGEST_CORRECT) from None
	
	try:
		un_swapped_request_slk_from: List[float] = [float(item) for item in str_request_slk_from]
		un_swapped_request_slk_to: List[float] = [float(item) for item in str_request_slk_to]
	except:
		raise URL_Parameter_Parse_Exception("error: parameters 'slk_from' and 'slk_to' could not be converted to numbers. " + ERROR_SUGGEST_CORRECT) from None
	
	# Fix reversed intervals
	request_slk_from: List[float] = []
	request_slk_to: List[float] = []
	for iter_slk_from, iter_slk_to in zip(un_swapped_request_slk_from, un_swapped_request_slk_to):
		request_slk_from.append(min(iter_slk_from, iter_slk_to))
		request_slk_to.append(max(iter_slk_from, iter_slk_to))
	
	# obtain offset
	raw_request_offset: Optional[str] = request.get("offset", None)
	if raw_request_offset is None or raw_request_offset == "":
		str_request_offset: List[str] = ['0'] * len(request_roads)
	else:
		str_request_offset: List[str] = raw_request_offset.split(',')
	
	if len(str_request_offset) != len(request_roads):
		raise URL_Parameter_Parse_Exception(f"error: optional parameter 'offset={raw_request_offset}' list must be the same length as the 'road' parameter. {ERROR_SUGGEST_CORRECT_ADVANCED}") from None
	
	# convert offsets to floats
	try:
		request_offset = [float(item) if item != "" else 0 for item in str_request_offset]
	except:
		raise URL_Parameter_Parse_Exception(f"error: optional parameter 'offset={raw_request_offset}' could not be converted to a number. {ERROR_SUGGEST_CORRECT_ADVANCED}") from None
	
	raw_request_carriageway: Optional[str] = request.get("cway", None)
	if raw_request_carriageway is None or raw_request_carriageway == "":
		unsorted_request_carriageway = ["LRS"] * len(request_roads)
	else:
		unsorted_request_carriageway = raw_request_carriageway.split(',')
	
	if len(unsorted_request_carriageway) != len(request_roads):
		raise URL_Parameter_Parse_Exception(f"error: optional parameter 'cway={raw_request_carriageway}' list must be the same length as the 'road' parameter. {ERROR_SUGGEST_CORRECT_ADVANCED}") from None
	
	request_carriageway: List[str] = [''.join(sorted(item.upper())) if item != "" else "LRS" for item in unsorted_request_carriageway]
	
	return [Slice_Request_Args(*item) for item in zip(request_roads, request_slk_from, request_slk_to, request_offset, request_carriageway)]
