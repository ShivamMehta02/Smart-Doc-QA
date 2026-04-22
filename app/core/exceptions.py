from fastapi import HTTPException, status


class AppBaseException(Exception):
    """Base for all custom exceptions."""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class DocumentNotFoundError(AppBaseException):
    def __init__(self, doc_id: str):
        super().__init__(f"Document {doc_id} not found", 404)


class DocumentNotReadyError(AppBaseException):
    def __init__(self, doc_id: str, status: str):
        super().__init__(f"Document {doc_id} is not ready (status: {status})", 409)


class DuplicateDocumentError(AppBaseException):
    def __init__(self, file_hash: str):
        super().__init__(f"Document already exists (hash: {file_hash[:8]}...)", 409)


class UnsupportedFileTypeError(AppBaseException):
    def __init__(self, filename: str):
        super().__init__(f"File type not supported: {filename}. Use PDF or DOCX.", 422)


class FileTooLargeError(AppBaseException):
    def __init__(self, size_mb: float, max_mb: int):
        super().__init__(f"File size {size_mb:.1f}MB exceeds limit of {max_mb}MB", 413)


class CorruptFileError(AppBaseException):
    def __init__(self, filename: str):
        super().__init__(f"Could not parse file: {filename}. File may be corrupt.", 422)


class OpenAIUnavailableError(AppBaseException):
    def __init__(self):
        super().__init__("OpenAI service is unavailable. Please try again later.", 503)


class OpenAIKeyMissingError(AppBaseException):
    def __init__(self):
        super().__init__("OpenAI API key is not configured.", 500)


class JobNotFoundError(AppBaseException):
    def __init__(self, job_id: str):
        super().__init__(f"Job {job_id} not found", 404)


class NoAnswerFoundError(AppBaseException):
    def __init__(self):
        super().__init__("Answer not found in the provided document.", 200)


class ConversationNotFoundError(AppBaseException):
    def __init__(self, conv_id: str):
        super().__init__(f"Conversation {conv_id} not found", 404)
