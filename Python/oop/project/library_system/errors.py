class LibraryError(Exception):
    pass


class ValidationError(LibraryError):
    pass


class BookNotFound(LibraryError):
    pass


class MemberNotFound(LibraryError):
    pass


class DuplicateBook(LibraryError):
    pass


class DuplicateMember(LibraryError):
    pass


class BookNotAvailable(LibraryError):
    pass


class LoanLimitReached(LibraryError):
    pass


class InvalidReturn(LibraryError):
    pass