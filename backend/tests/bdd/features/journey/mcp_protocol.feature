Feature: MCP Protocol Compliance
  As a developer integrating with the AI Job Engine
  I want to ensure MCP protocol compliance
  So that all tool responses follow the standard format

  Background:
    Given the MCP server is running
    And I have valid authentication

  @mcp @protocol @response_format
  Scenario: Validate MCP-wrapped response structure
    Given a journey exists
    When I perform a list journeys operation
    Then the response should be MCP-wrapped
    And the response should have "content" array
    And content[0] should have "text" field
    And the text should contain valid JSON

  @mcp @protocol @success_response
  Scenario: Validate successful operation response format
    Given a journey "JRN-MCP-001" exists
    When I read the journey
    Then the response should follow MCP success format:
      | field     |
      | status    |
      | message   |
      | operation |
      | data      |
      | timestamp |

  @mcp @protocol @error_response
  Scenario: Validate error response format
    When I try to read non-existent journey "INVALID-JRN"
    Then the response should follow MCP error format:
      | field        |
      | status       |
      | message      |
      | operation    |
      | error_code   |
      | timestamp    |

  @mcp @protocol @camelcase
  Scenario: Verify camelCase field naming convention
    Given a journey exists
    When I list all journeys
    Then all journey fields should use camelCase:
      | field            |
      | journeyId        |
      | odaComponentType |
      | createdAt        |
      | updatedAt        |
      | currentStageId   |

  @mcp @protocol @timestamps
  Scenario: Validate ISO 8601 timestamp format
    When I perform any journey operation
    Then all timestamps should be in ISO 8601 format
    And timestamps should include timezone information

  @mcp @protocol @metadata
  Scenario: Validate response metadata for list operations
    When I list all journeys
    Then the response metadata should include:
      | field       |
      | total_count |
      | timestamp   |

  @mcp @protocol @pagination
  Scenario: Validate pagination metadata
    Given multiple journeys exist
    When I list journeys with pagination
    Then the metadata should include:
      | field      |
      | total_count|
      | page       |
      | page_size  |

  @mcp @protocol @tool_chaining
  Scenario: Validate tool chaining compatibility
    Given a journey "JRN-CHAIN-001" exists
    When I create a job for the journey
    And I retrieve job logs
    Then both operations should return MCP-compliant responses
    And I should be able to chain the job_id from first to second operation

  @mcp @protocol @error_codes
  Scenario: Validate standardized error codes
    When I perform operations that trigger errors:
      | operation           | expected_error_code |
      | read invalid journey| JOURNEY_NOT_FOUND   |
      | delete without ID   | VALIDATION_ERROR    |
      | invalid action      | INVALID_ACTION      |
    Then each error should have appropriate error code

  @mcp @protocol @http_status
  Scenario: Validate HTTP status codes
    Given a journey exists
    When I perform a valid operation
    Then HTTP status should be 200
    When I perform an invalid operation
    Then HTTP status should be 4xx or 5xx

  @mcp @protocol @cors
  Scenario: Validate CORS headers
    When I make a cross-origin request
    Then the response should include CORS headers:
      | header                      |
      | Access-Control-Allow-Origin |
      | Access-Control-Allow-Methods|
      | Access-Control-Allow-Headers|

  @mcp @protocol @content_type
  Scenario: Validate content-type headers
    When I make any API request
    Then the response Content-Type should be "application/json"

  @mcp @protocol @json_rpc
  Scenario: Validate JSON-RPC compatibility
    When I make a request in JSON-RPC format
    Then the response should be JSON-RPC compliant
    And it should have:
      | field   |
      | jsonrpc |
      | id      |
      | result  |

  @mcp @protocol @streaming
  Scenario: Validate MCP streaming support
    Given a journey with large dataset
    When I request comprehensive journey data
    Then the response should support streaming
    And data should be returned incrementally

  @mcp @protocol @versioning
  Scenario: Validate API versioning support
    When I make a request with API version header
    Then the response should respect the version
    And version-specific features should be available

  @mcp @protocol @rate_limiting
  Scenario: Validate rate limiting headers
    When I make multiple rapid requests
    Then responses should include rate limit headers:
      | header               |
      | X-RateLimit-Limit    |
      | X-RateLimit-Remaining|
      | X-RateLimit-Reset    |

