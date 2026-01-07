// Neo4j Setup Script
// Run this script to configure read-only user and initialize schema

// =============================================================================
// STEP 1: Create Read-Only User
// =============================================================================

// Create the read-only user
CREATE USER readonly_user SET PASSWORD 'change_this_password' SET PASSWORD CHANGE NOT REQUIRED;

// Grant reader role (read access to all databases)
GRANT ROLE reader TO readonly_user;

// Explicitly deny write operations
DENY WRITE ON DATABASE * TO readonly_user;
DENY CREATE ON DATABASE * TO readonly_user;
DENY DELETE ON DATABASE * TO readonly_user;
DENY SET LABEL ON DATABASE * TO readonly_user;
DENY REMOVE LABEL ON DATABASE * TO readonly_user;
DENY SET PROPERTY ON DATABASE * TO readonly_user;

// =============================================================================
// STEP 2: Initialize Schema (run as admin/rw user)
// =============================================================================

// Create index on Entity.name for faster lookups
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);

// Create unique constraint on Entity.name to prevent duplicates
CREATE CONSTRAINT entity_name_unique IF NOT EXISTS FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// Create index on Entity.type for type-based queries
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);

// =============================================================================
// STEP 3: Verify Read-Only Permissions
// =============================================================================

// Test that read-only user cannot write (should fail)
// Connect as readonly_user and run:
// CREATE (test:TestNode {name: 'security_check'});
// Expected: Permission denied error

// Test that read-only user can read (should succeed)
// MATCH (n) RETURN count(n) LIMIT 1;
// Expected: Returns count

// =============================================================================
// STEP 4: Optional - Create Additional Indexes for Performance
// =============================================================================

// Index for entity descriptions (full-text search)
// CREATE FULLTEXT INDEX entity_description IF NOT EXISTS FOR (e:Entity) ON EACH [e.description];

// Index for relationship descriptions
// CREATE INDEX relationship_description IF NOT EXISTS FOR ()-[r]-() ON (r.description);

// =============================================================================
// VERIFICATION QUERIES
// =============================================================================

// List all users
SHOW USERS;

// Show privileges for readonly_user
SHOW USER readonly_user PRIVILEGES;

// List all indexes
SHOW INDEXES;

// List all constraints
SHOW CONSTRAINTS;
