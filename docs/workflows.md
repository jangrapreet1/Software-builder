# Workflow Diagrams

## Main Build Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Input                                │
│                    (Project Brief)                               │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   1. ANALYZE BRIEF                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Parse project description                             │  │
│  │  • Extract features                                      │  │
│  │  • Identify entities                                     │  │
│  │  • Define user flows                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                 2. GENERATE SPECIFICATIONS                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Architecture design                                   │  │
│  │  • API endpoints                                         │  │
│  │  • Database schema                                       │  │
│  │  • Authentication strategy                               │  │
│  │  • Frontend structure                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    3. PLAN TASKS                                 │
│  ┌────────────────────────┐  ┌─────────────────────────────┐   │
│  │   Backend Tasks        │  │    Frontend Tasks           │   │
│  │  • Setup project       │  │  • Setup project            │   │
│  │  • Database models     │  │  • Auth pages               │   │
│  │  • Auth endpoints      │  │  • Main layout              │   │
│  │  • CRUD endpoints      │  │  • Feature pages            │   │
│  └────────────────────────┘  └─────────────────────────────┘   │
└────────────────────────────┬───────────────┬────────────────────┘
                             ↓               ↓
            ┌────────────────────────────────────────────┐
            ↓                                            ↓
┌──────────────────────────┐              ┌──────────────────────────┐
│   4. GENERATE BACKEND    │              │   5. GENERATE FRONTEND   │
│  ┌────────────────────┐  │              │  ┌────────────────────┐  │
│  │ • FastAPI app      │  │              │  │ • React app        │  │
│  │ • Models           │  │              │  │ • Components       │  │
│  │ • Schemas          │  │              │  │ • Pages            │  │
│  │ • Routes           │  │              │  │ • API client       │  │
│  │ • Auth             │  │              │  │ • Auth context     │  │
│  │ • Tests            │  │              │  │ • Routing          │  │
│  └────────────────────┘  │              │  └────────────────────┘  │
└────────────┬─────────────┘              └──────────┬───────────────┘
             └────────────────┬──────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   6. INTEGRATE CODE                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Combine backend and frontend                          │  │
│  │  • Create project structure                              │  │
│  │  • Generate Docker Compose                               │  │
│  │  • Setup environment files                               │  │
│  │  • Create README                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                   7. VALIDATE BUILD                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Check file existence                                  │  │
│  │  • Validate syntax                                       │  │
│  │  • Run linters                                           │  │
│  │  • Execute tests                                         │  │
│  │  • Verify Docker configuration                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    8. DEPLOY APP                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Build Docker containers                               │  │
│  │  • Start services                                        │  │
│  │  • Run health checks                                     │  │
│  │  • Provide access URLs                                   │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ✓ APPLICATION READY                           │
│              Frontend: http://localhost:3000                     │
│              Backend: http://localhost:8000                      │
└─────────────────────────────────────────────────────────────────┘
```

## Agent Collaboration Flow

```
┌─────────────┐
│ Coordinator │
│    Agent    │
└──────┬──────┘
       │
       │ Task Assignment
       ├────────────────────┐
       │                    │
       ↓                    ↓
┌──────────────┐    ┌──────────────┐
│   Backend    │    │   Frontend   │
│    Agent     │    │    Agent     │
└──────┬───────┘    └──────┬───────┘
       │                   │
       │ Need Clarification│
       ├───────────────────┤
       │                   │
       ↓                   ↓
┌─────────────────────────────┐
│  AutoGen Collaboration      │
│     • Discussion            │
│     • Conflict Resolution   │
│     • Consensus Building    │
└──────────────┬──────────────┘
               │
               │ Resolution
               ↓
       ┌──────────────┐
       │  Semantic    │
       │   Kernel     │
       │  • Validate  │
       │  • Format    │
       │  • Test      │
       └──────┬───────┘
              │
              │ Validated Code
              ↓
       ┌──────────────┐
       │ Integration  │
       │    Agent     │
       └──────┬───────┘
              │
              ↓
       [Final Output]
```

## State Transitions

```
INITIALIZING
    ↓
ANALYZING
    ↓
GENERATING_SPECS
    ↓
PLANNING_TASKS
    ↓
    ├→ GENERATING_BACKEND
    │       ↓
    │   BACKEND_COMPLETE
    │       ↓
    └→ GENERATING_FRONTEND
            ↓
        FRONTEND_COMPLETE
            ↓
        INTEGRATING
            ↓
        VALIDATING
            ↓
        ├→ VALIDATION_PASSED → DEPLOYING → SUCCESS
            └→ VALIDATION_FAILED → FAILED
```

## Error Recovery Flow

```
[Task Execution]
       ↓
   [Error Occurs]
       ↓
 [Log Error Details]
       ↓
 [Check Retry Count]
       ↓
   ┌───┴───┐
   │       │
[< Max]  [= Max]
   │       │
   ↓       ↓
[Retry] [Report Failure]
   │       │
   └───┬───┘
       ↓
[Update State]
       ↓
  [Continue]
```

## Clarification Request Flow

```
Agent encounters ambiguity
       ↓
Create clarification request
       ↓
Send to Coordinator
       ↓
Coordinator analyzes context
       ↓
    ┌──┴──┐
    │     │
[Clear] [Unclear]
    │     │
    │     └→ Use LLM to infer
    │            ↓
    └────────────┤
                 ↓
         Provide response
                 ↓
         Agent continues
```

## Conflict Resolution Flow

```
Multiple agents propose solutions
            ↓
    Coordinator receives all proposals
            ↓
    Evaluate against criteria:
      • Simplicity
      • Maintainability
      • Performance
      • Best practices
            ↓
    ┌──────┴──────┐
    │             │
[Clear winner] [Tie]
    │             │
    │             └→ LLM evaluation
    │                    ↓
    └────────────────────┤
                         ↓
                 Select solution
                         ↓
              Notify all agents
                         ↓
              Update specifications
```

## Parallel Execution

```
                [Coordinator]
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ↓             ↓             ↓
  [Backend Agent] [Frontend]  [Test Agent]
        │         [Agent]          │
        │             │             │
    (parallel execution)            │
        │             │             │
        └─────────────┼─────────────┘
                      │
              [Integration Agent]
```

## Progress Tracking

```
Step 1: Analyze Brief         [====      ] 20%
Step 2: Generate Specs         [========  ] 30%
Step 3: Plan Tasks             [========= ] 40%
Step 4: Generate Backend       [===========] 55%
Step 5: Generate Frontend      [=============] 70%
Step 6: Integrate Code         [===============] 85%
Step 7: Validate Build         [=================] 95%
Step 8: Deploy App             [==================] 100%
```

## Build Retry Logic

```
[Build Step]
     ↓
  Execute
     ↓
  ┌──┴──┐
  │     │
[OK]  [FAIL]
  │     │
  │     ↓
  │  Retry Count++
  │     ↓
  │  ┌──┴──┐
  │  │     │
  │ [<3]  [≥3]
  │  │     │
  │  └→ Retry
  │        │
  └────────┴→ Continue
```

## LangGraph State Flow

```
Initial State
    ↓
[analyze_brief]
    ↓
State Update: features, entities, user_flows
    ↓
[generate_specs]
    ↓
State Update: technical_specs
    ↓
[plan_tasks]
    ↓
State Update: backend_tasks, frontend_tasks
    ↓
[generate_backend]
    ↓
State Update: backend_code
    ↓
[generate_frontend]
    ↓
State Update: frontend_code
    ↓
[integrate_code]
    ↓
State Update: integrated_code, source_path
    ↓
[validate_build]
    ↓
State Update: test_results
    ↓
[deploy_app]
    ↓
Final State: app_url, build_status
```

## Monitoring & Logging

```
[Event Occurs]
     ↓
[Create Log Entry]
     ↓
   {
     level: "info|warning|error",
     message: "...",
     timestamp: "...",
     context: {...}
   }
     ↓
[Store in State]
     ↓
[Send to UI]
     ↓
[Display in Real-time]
```
