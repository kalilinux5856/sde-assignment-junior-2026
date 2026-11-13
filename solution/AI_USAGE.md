# AI Usage Disclosure

## Tools Used

- ChatGPT (OpenAI)

## What I Used AI For

I used ChatGPT as a technical learning, architecture, implementation, code-review, and debugging assistant throughout Assignment A.

The project was developed through an iterative, phase-by-phase process. I used ChatGPT to understand the requirements, plan the architecture, generate implementation code for individual files, understand how the components interacted, and verify the behavior of the completed pipeline.

The assistance covered the following areas:

- **Requirement analysis:** Breaking down the assignment specification into smaller implementation phases, understanding individual requirements, identifying dependencies, and deciding the order in which different components should be developed.

- **Architecture and database design:** Discussing the overall system architecture, planning the SQLite database schema, understanding table relationships, identifying constraints and indexes, and deciding how responsibilities should be distributed across modules.

- **Implementation and code generation:** Getting assistance in writing and refining code for individual files, including database management, PII protection, normalization, lead ingestion, event ingestion, event linking, call reconstruction, classification, reporting, and the main execution pipeline.

- **Technical explanations:** Understanding Python concepts, SQL queries, database operations, encryption, event processing, transaction handling, timestamp normalization, and the reasoning behind implementation decisions.

- **Testing and debugging:** Generating test cases, understanding test failures, investigating execution errors, tracing function calls across modules, and correcting implementation issues.

- **Code review and architectural refinement:** Examining function definitions, imports, function calls, module responsibilities, and dependencies to identify missing functionality, inconsistencies, and areas requiring improvement.

- **Verification:** Checking idempotency, duplicate handling, PII protection, event immutability, data consistency, and the correctness of generated reports through automated tests and direct database inspection.

- **Documentation:** Getting assistance in preparing the submission documentation and explaining the architecture, implementation decisions, limitations, testing approach, and AI usage.

## Why I Chose ChatGPT

I deliberately chose ChatGPT for this assignment instead of relying on AI coding agents or assistants such as Claude Code, Codex, or similar tools that can directly architect, generate, and modify large parts of a codebase.

Although those tools can potentially complete implementation tasks much faster, my objective was not simply to produce a working project in the shortest possible time. I wanted to understand how a real software project is structured, how architectural decisions are made, how individual modules interact, and how the implementation is tested and maintained.

ChatGPT's conversational and iterative approach suited this objective. Rather than having the entire repository generated and modified automatically, I worked through the project in smaller stages. I discussed the architecture, requested explanations, reviewed suggested code, made changes in my local repository, executed commands, inspected database records, examined generated reports, and ran tests before moving forward.

This approach required considerably more active involvement from my side and took longer than a largely automated coding workflow. However, it encouraged me to question implementation decisions, understand individual functions, identify missing functionality, investigate errors, and verify actual outputs instead of simply accepting generated code.

My intention was to use AI as a development and learning assistant, not as a substitute for understanding the engineering work. I wanted to build something that I could explain, debug, maintain, and extend independently rather than simply obtain a codebase that appeared to work.

## What I Contributed

I actively drove the development process and worked through the assignment in structured phases, from understanding the requirements and planning the architecture to implementing individual components, integrating them, testing, debugging, and verifying the final output.

ChatGPT assisted with explanations, implementation code, and test generation, but I was actively involved in deciding what needed to be implemented, understanding how it should work, reviewing the suggested code, questioning design decisions, and checking the actual results.

My contributions included:

**1. Requirement analysis and development planning**

I worked through the assignment specification step by step, breaking it into smaller requirements and understanding what each stage of the pipeline needed to accomplish.

Rather than attempting to implement the entire system at once, I followed a phased approach. I first worked on understanding the database structure, followed by lead ingestion, event ingestion, event linking, call reconstruction, classification, reporting, and final verification.

**2. Architecture and design decisions**

I actively participated in understanding and shaping the architecture before and during implementation.

This included understanding why particular database tables were required, what information each table should store, how records should be related, and how data should move between different processing stages.

I also questioned implementation decisions when I felt that responsibilities were being mixed or the suggested approach did not fit the overall architecture.

For example, I questioned placing event-to-lead linking inside the event ingestion module and suggested keeping these responsibilities separate.

**3. Phase-by-phase implementation**

I worked through the implementation file by file and feature by feature, with ChatGPT assisting in generating and refining code.

The implementation covered:

- Database initialization, connection management, and schema creation.
- PII encryption, decryption, and phone hashing.
- Field normalization and validation.
- Lead ingestion, duplicate detection, and merging.
- Event parsing, validation, deduplication, and storage.
- Linking previously unlinked events to leads.
- Reconstructing calls from individual events.
- Applying effective disposition rules and classifying leads.
- Generating the required CSV and JSON reports.
- Integrating the complete workflow through the main execution module.

I did not treat the generated code as a black box. I worked through the implementation in stages, asking for explanations of individual functions and how they contributed to the complete processing flow.

**4. Detailed code review and understanding**

A significant part of my involvement was understanding the actual implementation rather than merely getting the code to execute.

I reviewed the code in detail, function by function and line by line as we progressed. I examined what each function was intended to do, what inputs it accepted, what it returned, which other functions it depended on, and where it was being used.

I also checked whether functions were actually defined and called correctly, whether imports matched the existing project structure, and whether individual modules were performing their intended responsibilities.

Whenever I did not understand a particular implementation choice, I asked for an explanation before proceeding.

**5. Debugging and problem-solving**

I actively participated in investigating errors and unexpected behavior.

This involved examining error messages, tracing execution across files, checking database records, identifying missing functionality, and correcting inconsistencies between function definitions and their usages.

I also questioned suggested approaches when they did not appear correct or did not account for the assignment's requirements.

**6. Testing and verification**

I consistently asked for test cases to verify the implementation instead of relying only on explanations or assumptions.

ChatGPT assisted in generating test code, while I worked through the expected behavior, ran the tests, examined the outputs, and investigated failures.

I also used the SQLite CLI to inspect actual database records, executed queries to verify record counts and relationships, examined generated reports, and performed manual checks for important requirements.

The complete automated test suite contained 43 tests, all of which passed.

**7. Iterative refinement**

The implementation was not completed in a single pass. As we progressed, we revisited earlier decisions, corrected overlooked functionality, improved module separation, and addressed issues discovered during integration and testing.

I participated in these revisions by questioning the existing implementation, understanding the consequences of proposed changes, and verifying that the revised solution continued to work correctly.

My overall contribution was driving and participating in the complete development process, understanding the architecture, guiding implementation decisions, reviewing the generated code, investigating issues, and verifying the integrated solution. This process also helped me develop a much clearer understanding of how the complete pipeline works and how its individual components interact.

## Where the AI Was Wrong or Unhelpful

Although ChatGPT was useful throughout development, some suggestions were incomplete, inconsistent with the existing codebase, or required additional correction.

The following are examples of issues encountered during implementation.

**1. Missing or overlooked functionality**

During the phase-by-phase implementation, there were instances where certain functions or pieces of functionality were overlooked while moving to the next development stage.

We had to revisit previously implemented modules, identify what was missing, and implement the required functionality before continuing.

This reinforced the importance of checking the completeness of each module rather than assuming that finishing one implementation phase meant every required function was already present.

**2. Incorrect imports and dependencies**

Some suggested code referenced imports or modules that were not available in the existing project.

These issues surfaced during execution or testing and required checking the actual project structure, identifying the unavailable dependency, and correcting the imports.

**3. Function-name and integration inconsistencies**

There were instances where function definitions, imports, and function calls did not align across different modules.

In some cases, a function was referenced using a name that did not match its actual definition. These inconsistencies caused execution and test failures.

We resolved them by tracing the relevant function calls, checking definitions and usages across files, and correcting the references.

**4. Incomplete consideration of module responsibilities**

One example involved the `link_pending_events()` function. Initially, the suggested implementation placed event-to-lead linking inside the event ingestion module. I questioned this design because ingesting events and linking them to leads are separate responsibilities.

Event ingestion should parse, validate, deduplicate, normalize, and store incoming events. Event linking should operate on already-stored events and associate them with their corresponding leads.

This distinction was particularly important because events could arrive before their corresponding leads. Such events needed to remain stored as pending records and be linked when the leads arrived in a subsequent data drop.

We therefore moved the linking logic into a dedicated `event_linking.py` module. This also allowed linking to be performed independently and repeatedly without creating duplicate relationships.

**5. Edge-case handling**

An initial implementation did not properly account for events containing invalid phone numbers. This could prevent an otherwise valid event from being stored.

We investigated the behavior and corrected it so that the event could still be retained with a null phone hash and remain unlinked until a valid association was possible.

**6. Encryption key configuration and database initialization**

During the initial database setup, I overlooked configuring the PII encryption key before beginning the ingestion process. This meant that the database had to be initialized again after generating and configuring the key.

Although this required repeating the ingestion process, it was relatively straightforward because we had already implemented the complete pipeline for processing source files and populating the database tables. We could recreate the database and populate it again by running the existing pipeline.

To avoid repeating this issue, we configured the encryption key through an environment variable loaded from a `.env` file. This kept the key outside the source code and ensured that subsequent database initialization and ingestion runs used the configured key.

**7. UTC storage and IST reporting decision**

Another decision involved timestamp handling.

Initially, we considered using IST throughout the processing pipeline. However, during implementation, UTC normalization and storage had already been established. By the time I revisited the reporting requirement, the normalization logic, generated dataset, and database records were already based on UTC.

Changing the existing approach at that stage would have required revisiting timestamp normalization, stored records, event ordering, and related tests.

Rather than introducing unnecessary changes to an already functioning pipeline, we retained UTC as the internal storage format and converted timestamps to IST during report generation.

This allowed us to maintain consistent internal timestamp handling while ensuring that report dates and displayed timestamps followed the required IST timezone.

**8. Call reconstruction and test-case verification**

I suggested approaching call processing through the reconstruction of individual call records rather than treating every event as an independent interaction.

A single call can generate multiple events, including initiation, connection, completion, and disposition updates. Determining the outcome of a call therefore requires combining related events and considering their timestamps.

We developed the call reconstruction logic around this approach, grouping events using their workflow and call identifiers before determining the call outcome.

Throughout implementation, I repeatedly asked for test cases to verify the behavior of the logic. ChatGPT assisted in generating the test code, but I wanted to examine the expected behavior and actual output rather than accepting an implementation simply because it appeared logically correct.

For example, we tested missing call initiation events, multiple disposition updates, disposition overrides, and the precedence of the latest override.

These examples demonstrate that AI-generated suggestions sometimes needed correction, additional implementation, or reconsideration of their architectural placement. Reviewing the code, questioning suggestions, tracing errors, and testing actual behavior were essential throughout development.

## How I Verified AI-Generated Code

I treated AI-generated code as implementation assistance rather than automatically correct solutions.

Verification was performed throughout development using automated tests, direct code inspection, SQL queries, and repeated execution of the complete pipeline.

The verification process included:

- Running the generated assignment dataset through the complete pipeline.
- Inspecting CSV and JSONL input files to understand the actual data being processed.
- Reviewing Python function definitions, imports, references, parameters, return values, and interactions across modules.
- Executing SQL queries to inspect database tables, relationships, record counts, and ingestion outcomes.
- Checking lead insertion, duplicate lead merging, event deduplication, event-to-lead linking, and orphan event handling.
- Running the automated test suite, with all 43 tests passing.
- Re-running the complete pipeline and confirming that database record counts remained unchanged.
- Comparing SHA-256 hashes of generated reports before and after a subsequent pipeline execution to verify identical outputs.
- Checking that raw phone fields were absent from stored event payloads.
- Verifying that encrypted PII could be successfully decrypted using the configured encryption key.
- Testing database triggers to confirm that UPDATE and DELETE operations on the events table were rejected.
- Reviewing generated reports and comparing aggregate results for consistency.

The project was developed through repeated cycles of requirement analysis, architecture planning, implementation, code review, integration, testing, debugging, and refinement.

ChatGPT assisted with technical explanations, code generation, test generation, and debugging. I actively participated in directing this process, understanding the implementation, questioning design decisions, investigating issues, and verifying the final behavior.

This approach helped me understand not only the individual functions and modules but also how the complete ingestion and reporting pipeline operates as an integrated system.