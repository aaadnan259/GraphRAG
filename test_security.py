"""
Security Testing Script
Verifies that read-only user permissions are properly configured.
"""

import sys
from config import config, ConfigurationError
from database import verify_read_only_permissions, get_read_graph, get_write_graph


def test_configuration():
    """Test that all required configuration is present."""
    print("=" * 60)
    print("Testing Configuration...")
    print("=" * 60)

    try:
        print(f"✓ Google API Key: {config.google_api_key[:10]}...")
        print(f"✓ Neo4j URI: {config.neo4j_uri}")
        print(f"✓ Neo4j RW User: {config.neo4j_rw_user}")
        print(f"✓ Neo4j RO User: {config.neo4j_ro_user}")
        print(f"✓ Chunk Size: {config.chunk_size}")
        print(f"✓ LLM Model: {config.llm_model}")
        print(f"✓ Embedding Model: {config.embedding_model}")
        print("\n✓ Configuration validation PASSED\n")
        return True
    except ConfigurationError as e:
        print(f"\n✗ Configuration validation FAILED: {e}\n")
        return False


def test_neo4j_connectivity():
    """Test Neo4j database connectivity."""
    print("=" * 60)
    print("Testing Neo4j Connectivity...")
    print("=" * 60)

    try:
        print("\nTesting WRITE connection...")
        write_driver = get_write_graph()
        write_driver.verify_connectivity()
        print("✓ Write connection successful")

        print("\nTesting READ connection...")
        read_driver = get_read_graph()
        read_driver.verify_connectivity()
        print("✓ Read connection successful")

        print("\n✓ Neo4j connectivity PASSED\n")
        return True
    except Exception as e:
        print(f"\n✗ Neo4j connectivity FAILED: {e}\n")
        return False


def test_read_only_permissions():
    """Test that read-only user cannot perform write operations."""
    print("=" * 60)
    print("Testing Read-Only Permissions...")
    print("=" * 60)

    try:
        read_driver = get_read_graph()
        result = verify_read_only_permissions(read_driver)

        if result:
            print("\n✓ Read-only permissions PASSED")
            print("  The read-only user is properly restricted from write operations.\n")
            return True
        else:
            print("\n✗ Read-only permissions FAILED")
            print("  SECURITY VIOLATION: Read-only user can perform write operations!")
            print("  Please configure Neo4j to restrict write access for the RO user.\n")
            return False
    except Exception as e:
        print(f"\n✗ Read-only permissions test ERROR: {e}\n")
        return False


def test_relationship_schema_validation():
    """Test relationship type normalization."""
    print("=" * 60)
    print("Testing Relationship Schema Validation...")
    print("=" * 60)

    from models import normalize_relation_type, ALLOWED_RELATION_TYPES

    test_cases = [
        ("WORKS_AT", "WORKS_AT"),
        ("works_at", "WORKS_AT"),
        ("CEO_OF", "MANAGES"),
        ("WORKS_FOR", "WORKS_AT"),
        ("LOCATED_AT", "LOCATED_IN"),
        ("UNKNOWN_RELATION", "RELATED_TO"),
        ("invalid!@#relation", "RELATED_TO"),
    ]

    all_passed = True

    for input_rel, expected in test_cases:
        result = normalize_relation_type(input_rel)
        if result == expected:
            print(f"✓ '{input_rel}' → '{result}'")
        else:
            print(f"✗ '{input_rel}' → '{result}' (expected '{expected}')")
            all_passed = False

    if all_passed:
        print(f"\n✓ All {len(test_cases)} test cases PASSED")
        print(f"  Allowed relation types: {len(ALLOWED_RELATION_TYPES)}\n")
        return True
    else:
        print("\n✗ Some test cases FAILED\n")
        return False


def test_input_sanitization():
    """Test input sanitization."""
    print("=" * 60)
    print("Testing Input Sanitization...")
    print("=" * 60)

    from models import sanitize_text

    test_cases = [
        ("Normal text", "Normal text"),
        ("Text with <script>alert('xss')</script>", "Text with scriptalertxssscript"),
        ("SQL'; DROP TABLE users;--", "SQL DROP TABLE users"),
        ("  Whitespace  ", "Whitespace"),
        ("A" * 600, "A" * 500),
    ]

    all_passed = True

    for input_text, expected_contains in test_cases:
        result = sanitize_text(input_text)
        safe = (
            len(result) <= 500 and
            '<' not in result and
            '>' not in result and
            ';' not in result
        )

        if safe:
            print(f"✓ '{input_text[:30]}...' → sanitized")
        else:
            print(f"✗ '{input_text[:30]}...' → NOT properly sanitized")
            all_passed = False

    if all_passed:
        print(f"\n✓ Input sanitization PASSED\n")
        return True
    else:
        print("\n✗ Input sanitization FAILED\n")
        return False


def main():
    """Run all security tests."""
    print("\n")
    print("=" * 60)
    print(" GraphRAG Security Test Suite")
    print("=" * 60)
    print("\n")

    results = []

    results.append(("Configuration", test_configuration()))
    results.append(("Neo4j Connectivity", test_neo4j_connectivity()))
    results.append(("Read-Only Permissions", test_read_only_permissions()))
    results.append(("Relationship Schema", test_relationship_schema_validation()))
    results.append(("Input Sanitization", test_input_sanitization()))

    print("=" * 60)
    print(" Test Results Summary")
    print("=" * 60)
    print()

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:10} - {test_name}")
        if not passed:
            all_passed = False

    print()
    print("=" * 60)

    if all_passed:
        print("✓ ALL TESTS PASSED - System is secure and ready for deployment")
        print("=" * 60)
        return 0
    else:
        print("✗ SOME TESTS FAILED - Please fix the issues before deployment")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
