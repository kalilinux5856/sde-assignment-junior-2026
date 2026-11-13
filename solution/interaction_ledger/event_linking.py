
def link_pending_events(connection):
    """
    Link stored events to leads.

    First, match events using workflow_id + phone_hash.
    Then, link phone-less events using another linked event
    from the same call.

    Returns the number of newly created links.
    """

    linked_count = 0

    # STEP 1: Find events that have not been linked yet
    # and have a phone hash available.
    pending_events = connection.execute("""
        SELECT
            e.event_id,
            e.workflow_id,
            e.phone_hash
        FROM events AS e
        LEFT JOIN event_lead_links AS l
            ON e.event_id = l.event_id
        WHERE
            l.event_id IS NULL
            AND e.phone_hash IS NOT NULL
    """).fetchall()

    # STEP 2: Find the matching lead for each event.
    for event in pending_events:

        lead = connection.execute("""
            SELECT id
            FROM leads
            WHERE workflow_id = ?
              AND phone_hash = ?
        """, (
            event["workflow_id"],
            event["phone_hash"]
        )).fetchone()

        # STEP 3: If a lead exists, create the relationship.
        if lead:
            connection.execute("""
                INSERT OR IGNORE INTO event_lead_links
                    (event_id, lead_id)
                VALUES (?, ?)
            """, (
                event["event_id"],
                lead["id"]
            ))

            linked_count += 1

    # STEP 4: Handle events that don't have a phone hash.
    # Repeat because linking one event may allow other events
    # from the same call to be linked.
    while True:

        newly_linked = 0

        pending_events = connection.execute("""
            SELECT
                e.event_id,
                e.workflow_id,
                e.call_id
            FROM events AS e
            LEFT JOIN event_lead_links AS l
                ON e.event_id = l.event_id
            WHERE l.event_id IS NULL
        """).fetchall()

        for event in pending_events:

            # Look for another event from the same call
            # that has already been linked to a lead.
            sibling = connection.execute("""
                SELECT l.lead_id
                FROM events AS sibling
                JOIN event_lead_links AS l
                    ON sibling.event_id = l.event_id
                WHERE sibling.workflow_id = ?
                  AND sibling.call_id = ?
                LIMIT 1
            """, (
                event["workflow_id"],
                event["call_id"]
            )).fetchone()

            if sibling:
                connection.execute("""
                    INSERT OR IGNORE INTO event_lead_links
                        (event_id, lead_id)
                    VALUES (?, ?)
                """, (
                    event["event_id"],
                    sibling["lead_id"]
                ))

                newly_linked += 1

        linked_count += newly_linked

        # Nothing more can be linked in this pass.
        if newly_linked == 0:
            break

    return linked_count
