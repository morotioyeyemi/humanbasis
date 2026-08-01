"""Typed errors for the SNP contract layer."""

from __future__ import annotations


class SNPError(Exception):
    """Base class for all SNP contract errors."""


class SchemaError(SNPError):
    """A message does not match the SNP envelope/payload schema."""


class UnknownEncodingError(SNPError):
    """The message references an encoding id that is not in the registry."""


class VectorLengthError(SNPError):
    """The vector length does not match the referenced encoding's declared length."""
