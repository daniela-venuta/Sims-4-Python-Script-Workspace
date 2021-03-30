from google.protobuf import descriptor
class RemoteArgs(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class Arg(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _REMOTEARGS_ARG

    DESCRIPTOR = _REMOTEARGS

class RemoteUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class Command(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _REMOTEUPDATE_COMMAND

    DESCRIPTOR = _REMOTEUPDATE

class CommandResponse(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _COMMANDRESPONSE

class KeyValResponse(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class KeyVal(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _KEYVALRESPONSE_KEYVAL

    DESCRIPTOR = _KEYVALRESPONSE

class SimTravelCommand(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SIMTRAVELCOMMAND
