class DomainError(Exception):
    status_code = 500


class RepositoryNotFoundError(DomainError):
    status_code = 404


class RefNotFoundError(DomainError):
    status_code = 404


class InvalidRequestError(DomainError):
    status_code = 422


class PathOutsideWorkspaceError(DomainError):
    status_code = 403


class GitOperationError(DomainError):
    status_code = 502


class AnalysisNotFoundError(DomainError):
    status_code = 404


class LLMProviderError(DomainError):
    status_code = 502


class SecurityIntegrationError(DomainError):
    status_code = 502


class ConfigurationError(DomainError):
    status_code = 500


class RagError(DomainError):
    status_code = 503


class AgentRunNotFoundError(DomainError):
    status_code = 404
