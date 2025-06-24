from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# Basic JSON-RPC Types
JSONRPC_VERSION = "2.0"
RequestId = Union[str, int, None]

class BaseRequest(BaseModel):
    method: str
    params: Optional[Dict[str, Any]] = None

class JSONRPCRequest(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, const=True)
    id: RequestId
    method: str
    params: Optional[Dict[str, Any]] = None

class JSONRPCNotification(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, const=True)
    method: str
    params: Optional[Dict[str, Any]] = None

class Error(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None

class JSONRPCErrorResponse(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, const=True)
    id: RequestId
    error: Error

class JSONRPCSuccessResponse(BaseModel):
    jsonrpc: str = Field(default=JSONRPC_VERSION, const=True)
    id: RequestId
    result: Dict[str, Any]

# General MCP Types from schema.ts

class BaseMetadata(BaseModel):
    name: str
    title: Optional[str] = None

class Implementation(BaseMetadata):
    version: str

# initialize
class ClientCapabilities(BaseModel):
    experimental: Optional[Dict[str, Any]] = None
    roots: Optional[Dict[str, Any]] = None
    sampling: Optional[Dict[str, Any]] = None
    elicitation: Optional[Dict[str, Any]] = None

class InitializeRequestParams(BaseModel):
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation

class ServerCapabilities(BaseModel):
    experimental: Optional[Dict[str, Any]] = None
    logging: Optional[Dict[str, Any]] = None
    completions: Optional[Dict[str, Any]] = None
    prompts: Optional[Dict[str, Any]] = None
    resources: Optional[Dict[str, Any]] = None
    tools: Optional[Dict[str, Any]] = None

class InitializeResult(BaseModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: Optional[str] = None

# ping - no params, empty result
class PingRequestParams(BaseModel):
    pass

class EmptyResult(BaseModel):
    pass

# completion/complete
class PromptReference(BaseMetadata):
    type: str = "ref/prompt"

class ResourceTemplateReference(BaseModel):
    type: str = "ref/resource"
    uri: str

class CompleteRequestParams(BaseModel):
    ref: Union[PromptReference, ResourceTemplateReference]
    argument: Dict[str, str]
    context: Optional[Dict[str, Any]] = None

class CompleteResult(BaseModel):
    completion: Dict[str, Any]

# logging/setLevel
class SetLevelRequestParams(BaseModel):
    level: str

# prompts/get
class GetPromptRequestParams(BaseModel):
    name: str
    arguments: Optional[Dict[str, str]] = None

class TextResourceContents(BaseModel):
    uri: str
    mimeType: Optional[str] = None
    text: str
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class BlobResourceContents(BaseModel):
    uri: str
    mimeType: Optional[str] = None
    blob: str # base64 encoded
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class Resource(BaseMetadata):
    uri: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None
    size: Optional[int] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class TextContent(BaseModel):
    type: str = "text"
    text: str
    annotations: Optional[Dict[str, Any]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class ImageContent(BaseModel):
    type: str = "image"
    data: str # base64
    mimeType: str
    annotations: Optional[Dict[str, Any]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class AudioContent(BaseModel):
    type: str = "audio"
    data: str # base64
    mimeType: str
    annotations: Optional[Dict[str, Any]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class ResourceLink(Resource):
    type: str = "resource_link"

class EmbeddedResource(BaseModel):
    type: str = "resource"
    resource: Union[TextResourceContents, BlobResourceContents]
    annotations: Optional[Dict[str, Any]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

ContentBlock = Union[TextContent, ImageContent, AudioContent, ResourceLink, EmbeddedResource]

class PromptMessage(BaseModel):
    role: str
    content: ContentBlock

class GetPromptResult(BaseModel):
    description: Optional[str] = None
    messages: List[PromptMessage]

# prompts/list
class ListPromptsRequestParams(BaseModel):
    cursor: Optional[str] = None

class PromptArgument(BaseMetadata):
    description: Optional[str] = None
    required: Optional[bool] = None

class Prompt(BaseMetadata):
    description: Optional[str] = None
    arguments: Optional[List[PromptArgument]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class ListPromptsResult(BaseModel):
    prompts: List[Prompt]
    nextCursor: Optional[str] = None

# resources/list
class ListResourcesRequestParams(BaseModel):
    cursor: Optional[str] = None

class ListResourcesResult(BaseModel):
    resources: List[Resource]
    nextCursor: Optional[str] = None

# resources/templates/list
class ListResourceTemplatesRequestParams(BaseModel):
    cursor: Optional[str] = None

class ResourceTemplate(BaseMetadata):
    uriTemplate: str
    description: Optional[str] = None
    mimeType: Optional[str] = None
    annotations: Optional[Dict[str, Any]] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class ListResourceTemplatesResult(BaseModel):
    resourceTemplates: List[ResourceTemplate]
    nextCursor: Optional[str] = None

# resources/read
class ReadResourceRequestParams(BaseModel):
    uri: str

class ReadResourceResult(BaseModel):
    contents: List[Union[TextResourceContents, BlobResourceContents]]

# resources/subscribe
class SubscribeRequestParams(BaseModel):
    uri: str

# resources/unsubscribe
class UnsubscribeRequestParams(BaseModel):
    uri: str

# tools/call
class CallToolRequestParams(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None

class CallToolResult(BaseModel):
    content: List[ContentBlock]
    structuredContent: Optional[Dict[str, Any]] = None
    isError: Optional[bool] = None

# tools/list
class ListToolsRequestParams(BaseModel):
    cursor: Optional[str] = None

class ToolAnnotations(BaseModel):
    title: Optional[str] = None
    readOnlyHint: Optional[bool] = None
    destructiveHint: Optional[bool] = None
    idempotentHint: Optional[bool] = None
    openWorldHint: Optional[bool] = None

class Tool(BaseMetadata):
    description: Optional[str] = None
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None
    annotations: Optional[ToolAnnotations] = None
    _meta: Optional[Dict[str, Any]] = Field(None, alias="_meta")

class ListToolsResult(BaseModel):
    tools: List[Tool]
    nextCursor: Optional[str] = None

# Notifications
class CancelledNotificationParams(BaseModel):
    requestId: RequestId
    reason: Optional[str] = None

class ProgressNotificationParams(BaseModel):
    progressToken: Union[str, int]
    progress: float
    total: Optional[float] = None
    message: Optional[str] = None

class InitializedNotificationParams(BaseModel):
    pass

class RootsListChangedNotificationParams(BaseModel):
    pass
