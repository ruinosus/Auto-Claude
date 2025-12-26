# End-to-End (E2E) Tests

This directory contains Playwright-based E2E tests for the Auto-Claude Electron application.

## Overview

The E2E tests verify the complete user experience and integration of features in the Electron app. They are designed to run without requiring a full Electron launch for most scenarios, using mock-based testing patterns.

## Test Suites

### 1. Analytics Dashboard (`analytics-dashboard.e2e.ts`)

Comprehensive tests for the Analytics Dashboard feature covering:

#### Infrastructure Tests (6 tests)
- Database creation with correct schema
- Sample data storage and retrieval
- Cost calculations (SUM of total_cost)
- Token calculations (SUM of input/output tokens)
- Active session tracking (null ended_at)
- Conversation grouping by spec_id

#### Data Flow Tests (5 tests)
- DB path resolution for valid projects
- DB path resolution for missing databases
- Token chart data transformation (aggregated by spec)
- Model distribution data transformation (by phase)
- Budget progress calculation

#### Error State Tests (4 tests)
- Missing project handling
- Missing database handling
- Empty database handling
- Database query error handling

#### Budget Manager Tests (4 tests)
- Budget progress at different thresholds
- 75% threshold alert triggering
- 90% threshold alert triggering
- Over budget (100%+) alert triggering

#### Chart Data Tests (4 tests)
- Cost chart data preparation with timestamps
- Budget limit line integration
- Token aggregation by spec for tokens chart
- Model/phase distribution calculation

#### Real-time Update Tests (3 tests)
- New conversation detection
- Session completion detection
- Total recalculation on database changes

#### UI Navigation Tests (2 tests - skipped by default)
- Launch Electron and navigate to Analytics view
- Display Analytics view with all components

#### Chart Rendering Tests (5 tests - skipped by default)
- CostChart renders LineChart with SVG
- TokensChart renders BarChart with bars
- ModelDistributionChart renders PieChart with sectors
- SessionDurationChart renders
- Overview cards display data

**Total: 34 tests (27 passing mock-based + 7 UI tests skipped by default)**

### 2. Main Flows (`flows.e2e.ts`)

Tests for core user workflows (currently skipped in CI):
- Add Project flow
- Create Task flow
- Start Task flow
- Complete Review flow

## Running the Tests

### Prerequisites

```bash
# Build the Electron app first
npm run build

# Install Playwright (if not already installed)
npx playwright install
```

### Run All E2E Tests

```bash
npm run test:e2e
```

### Run Specific Test Suite

```bash
# Analytics Dashboard tests only
npm run test:e2e -- analytics-dashboard.e2e.ts

# Main flows tests only
npm run test:e2e -- flows.e2e.ts
```

### Run with UI Mode (for debugging)

```bash
npx playwright test --ui --config=e2e/playwright.config.ts
```

### Run in Debug Mode

```bash
npx playwright test --debug --config=e2e/playwright.config.ts analytics-dashboard.e2e.ts
```

## Test Strategy

### Mock-Based Testing

Most tests use a mock-based approach that:
- Creates test databases and fixtures
- Simulates data flows without launching Electron
- Tests core business logic and data transformations
- Runs fast and reliably in CI/CD

### Benefits
- **Fast execution**: No Electron launch overhead
- **Reliable**: No UI timing issues
- **Focused**: Tests specific logic and data flows
- **CI-friendly**: Works in headless environments

### Test Data

Tests use isolated test directories:
- `/tmp/auto-claude-analytics-e2e` - Analytics Dashboard tests
- `/tmp/auto-claude-ui-e2e` - Main flow tests

All test data is cleaned up after each test run.

## Database Schema

The Analytics Dashboard tests create SQLite databases with this schema:

```sql
CREATE TABLE conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  spec_id TEXT NOT NULL,
  phase TEXT,
  started_at TIMESTAMP NOT NULL,
  ended_at TIMESTAMP,
  total_cost REAL DEFAULT 0,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  model TEXT
);

CREATE TABLE conversation_turns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER NOT NULL,
  turn_number INTEGER NOT NULL,
  timestamp TIMESTAMP NOT NULL,
  role TEXT NOT NULL,
  cost REAL DEFAULT 0,
  input_tokens INTEGER DEFAULT 0,
  output_tokens INTEGER DEFAULT 0,
  cache_creation_tokens INTEGER DEFAULT 0,
  cache_read_tokens INTEGER DEFAULT 0,
  FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

## Adding New Tests

When adding new E2E tests:

1. Follow the existing patterns in `analytics-dashboard.e2e.ts`
2. Use descriptive test names
3. Group related tests with `test.describe()`
4. Clean up test data in `afterEach()` hooks
5. Use mock-based testing when possible
6. Document what the test covers

### Example Test Structure

```typescript
test.describe('Feature Name E2E - Category', () => {
  test.beforeEach(() => {
    setupTestEnvironment();
  });

  test.afterEach(() => {
    cleanupTestEnvironment();
  });

  test('should do something specific', () => {
    // Arrange
    createTestData();

    // Act
    const result = performOperation();

    // Assert
    expect(result).toBe(expected);
  });
});
```

## CI/CD Integration

The tests are configured to:
- Run serially (1 worker) to avoid Electron conflicts
- Retry twice on failure in CI (`CI=true`)
- Skip Electron launch tests in headless CI
- Generate HTML reports for debugging

## Configuration

See `playwright.config.ts` for:
- Test timeout settings (60s default)
- Worker configuration (1 worker)
- Reporter settings (HTML reports)
- Retry settings (2 retries in CI)
- Screenshot/trace settings

## Troubleshooting

### Tests Timeout

Increase timeout in test:
```typescript
test('slow test', async () => {
  test.setTimeout(120000); // 2 minutes
  // test code
});
```

### Database Locked Errors

Ensure databases are properly closed:
```typescript
db.close();
```

### Test Data Not Cleaned Up

Check that `cleanupTestEnvironment()` is called in `afterEach()`.

### Electron Launch Fails

These tests are designed to work without Electron launch. If you need to test actual Electron behavior, see `flows.e2e.ts` for launch patterns.

## Coverage Summary

Current E2E test coverage:
- **Analytics Dashboard**: 34 tests total
  - 27 passing mock-based tests (infrastructure, data flow, errors, budget, charts, real-time)
  - 7 UI tests (navigation + chart rendering) - skipped by default, requires Electron build
- **Main Flows**: 4 test suites (currently skipped)

## Running UI Tests Manually

The UI Navigation and Chart Rendering tests are skipped by default because they require a built Electron app. To run them:

1. **Build the Electron app:**
   ```bash
   npm run build
   ```

2. **Remove `.skip` from the tests** in `analytics-dashboard.e2e.ts`:
   - Search for `test.skip('should launch Electron app`
   - Change to `test('should launch Electron app`
   - Do the same for other UI tests

3. **Run the tests:**
   ```bash
   npx playwright test --config=e2e/playwright.config.ts analytics-dashboard.e2e.ts
   ```

4. **Or run in UI mode for interactive debugging:**
   ```bash
   npx playwright test --ui --config=e2e/playwright.config.ts analytics-dashboard.e2e.ts
   ```

**Note:** UI tests are intentionally skipped in CI/CD pipelines as they require:
- Built Electron application
- Non-headless environment
- Longer execution time

## Spec Compliance

These E2E tests address the following spec requirements for Task 16 (Analytics Dashboard):

### Spec Requirement: UI Navigation Tests
- **Status:** Implemented
- **Tests:**
  - `should launch Electron app and navigate to Analytics view` - Clicks Analytics in sidebar, verifies view loads
  - `should display Analytics view with all components` - Verifies charts container, overview cards, and budget manager are present

### Spec Requirement: Chart Rendering Tests
- **Status:** Implemented
- **Tests:**
  - `should render CostChart with data` - Verifies LineChart SVG renders
  - `should render TokensChart with data` - Verifies BarChart bars render
  - `should render ModelDistributionChart with data` - Verifies PieChart sectors render
  - `should render SessionDurationChart` - Verifies chart component renders
  - `should display overview cards with data` - Verifies all data cards display

All spec compliance tests are implemented and ready to run once the Electron app is built.

## Future Improvements

Potential areas for expansion:
- Add visual regression testing for charts
- Add tests for real-time polling behavior
- Add tests for budget alert UI interactions
- Add tests for data export functionality
- Add performance benchmarks for large datasets
- Add accessibility testing for Analytics Dashboard
