from typing import Any, Union

from pydantic import BaseModel

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
    params: dict[str, Any] | None = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = JSONRPC_VERSION
    id: RequestId
    method: str
    params: dict[str, Any] | None = None


class JSONRPCNotification(BaseModel):
    jsonrpc: str = JSONRPC_VERSION
    method: str
    params: dict[str, Any] | None = None


class Error(BaseModel):
    code: int
    message: str
    data: Any | None = None


class JSONRPCErrorResponse(BaseModel):
    jsonrpc: str = JSONRPC_VERSION
    id: RequestId
    error: Error


class JSONRPCSuccessResponse(BaseModel):
    jsonrpc: str = JSONRPC_VERSION
    id: RequestId
    result: dict[str, Any]


# General MCP Types from schema.ts


class BaseMetadata(BaseModel):
    name: str
    title: str | None = None


class Implementation(BaseMetadata):
    version: str


# initialize
class ClientCapabilities(BaseModel):
    experimental: dict[str, Any] | None = None
    roots: dict[str, Any] | None = None
    sampling: dict[str, Any] | None = None
    elicitation: dict[str, Any] | None = None


class InitializeRequestParams(BaseModel):
    protocolVersion: str
    capabilities: ClientCapabilities
    clientInfo: Implementation


class ServerCapabilities(BaseModel):
    experimental: dict[str, Any] | None = None
    logging: dict[str, Any] | None = None
    completions: dict[str, Any] | None = None
    prompts: dict[str, Any] | None = None
    resources: dict[str, Any] | None = None
    tools: dict[str, Any] | None = None


class InitializeResult(BaseModel):
    protocolVersion: str
    capabilities: ServerCapabilities
    serverInfo: Implementation
    instructions: str | None = None


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
    ref: PromptReference | ResourceTemplateReference
    argument: dict[str, str]
    context: dict[str, Any] | None = None


class CompleteResult(BaseModel):
    completion: dict[str, Any]


# logging/setLevel
class SetLevelRequestParams(BaseModel):
    level: str


# prompts/get
class GetPromptRequestParams(BaseModel):
    name: str
    arguments: dict[str, str] | None = None


class TextResourceContents(BaseModel):
    uri: str
    mimeType: str | None = None
    text: str


class BlobResourceContents(BaseModel):
    uri: str
    mimeType: str | None = None
    blob: str  # base64 encoded


class Resource(BaseMetadata):
    uri: str
    description: str | None = None
    mimeType: str | None = None
    annotations: dict[str, Any] | None = None
    size: int | None = None


class TextContent(BaseModel):
    type: str = "text"
    text: str
    annotations: dict[str, Any] | None = None


class ImageContent(BaseModel):
    type: str = "image"
    data: str  # base64
    mimeType: str
    annotations: dict[str, Any] | None = None


class AudioContent(BaseModel):
    type: str = "audio"
    data: str  # base64
    mimeType: str
    annotations: dict[str, Any] | None = None


class ResourceLink(Resource):
    type: str = "resource_link"


class EmbeddedResource(BaseModel):
    type: str = "resource"
    resource: TextResourceContents | BlobResourceContents
    annotations: dict[str, Any] | None = None


ContentBlock = Union[
    TextContent, ImageContent, AudioContent, ResourceLink, EmbeddedResource
]


class PromptMessage(BaseModel):
    role: str
    content: ContentBlock


class GetPromptResult(BaseModel):
    description: str | None = None
    messages: list[PromptMessage]


# prompts/list
class ListPromptsRequestParams(BaseModel):
    cursor: str | None = None


class PromptArgument(BaseMetadata):
    description: str | None = None
    required: bool | None = None


class Prompt(BaseMetadata):
    description: str | None = None
    arguments: list[PromptArgument] | None = None


class ListPromptsResult(BaseModel):
    prompts: list[Prompt]
    nextCursor: str | None = None


# resources/list
class ListResourcesRequestParams(BaseModel):
    cursor: str | None = None


class ListResourcesResult(BaseModel):
    resources: list[Resource]
    nextCursor: str | None = None


# resources/templates/list
class ListResourceTemplatesRequestParams(BaseModel):
    cursor: str | None = None


class ResourceTemplate(BaseMetadata):
    uriTemplate: str
    description: str | None = None
    mimeType: str | None = None
    annotations: dict[str, Any] | None = None


class ListResourceTemplatesResult(BaseModel):
    resourceTemplates: list[ResourceTemplate]
    nextCursor: str | None = None


# resources/read
class ReadResourceRequestParams(BaseModel):
    uri: str


class ReadResourceResult(BaseModel):
    contents: list[TextResourceContents | BlobResourceContents]


# resources/subscribe
class SubscribeRequestParams(BaseModel):
    uri: str


# resources/unsubscribe
class UnsubscribeRequestParams(BaseModel):
    uri: str


# tools/call
class CallToolRequestParams(BaseModel):
    name: str
    arguments: dict[str, Any] | None = None


class CallToolResult(BaseModel):
    content: list[ContentBlock]
    structuredContent: dict[str, Any] | None = None
    isError: bool | None = None


# tools/list
class ListToolsRequestParams(BaseModel):
    cursor: str | None = None


class ToolAnnotations(BaseModel):
    title: str | None = None
    readOnlyHint: bool | None = None
    destructiveHint: bool | None = None
    idempotentHint: bool | None = None
    openWorldHint: bool | None = None


class Tool(BaseMetadata):
    description: str | None = None
    inputSchema: dict[str, Any]
    outputSchema: dict[str, Any] | None = None
    annotations: ToolAnnotations | None = None


class ListToolsResult(BaseModel):
    tools: list[Tool]
    nextCursor: str | None = None


# Notifications
class CancelledNotificationParams(BaseModel):
    requestId: RequestId
    reason: str | None = None


class ProgressNotificationParams(BaseModel):
    progressToken: str | int
    progress: float
    total: float | None = None
    message: str | None = None


class InitializedNotificationParams(BaseModel):
    pass


class RootsListChangedNotificationParams(BaseModel):
    pass
