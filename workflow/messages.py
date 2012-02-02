# dict keys for messages
OPERATION = 'operation' # ID of operation
INPUT_DATA = 'input' # input ID or list of input IDs (can be zero-length)
OUTPUT_DATA = 'output' # output ID or list of output ID's (can be zero-length)
IN_METADATA = 'input_metadata' # structured input (e.g., parameters)
OUT_METADATA = 'output_metadata' # structured output (e.g., log fields)
TIMESTAMP = 'timestamp' # time of observation / event
ACTORS = 'actors' # id(s) of person / entity responsible for event
DESCRIPTION = 'description' # text describing event (for human-readability)

# operations will be defined for specific codes
# input / output ID's depend on coeds
# input / output metadata should be text in a structured format (e.g., XML)

# timestamps should be in ISO 8601 UTC YYYY-mm-ddTHH:MM:ss.SZ
# actor ID's should be global ID's and not names
# description should be short and not in a structured format

