# Runner — Stateful Multi-Turn Execution Model

**Stand:** 2026-10-03 · löst die P1/P3-Architekturfrage

## Die Entscheidung (Engine-Gap aufgelöst)

Der Plan wählte „Stateful-Rerun" (Option b: Subagent-Session offenhalten, Turns nachschieben). Real ist das **nicht baubar**: `delegate_task` spawnt ein Child mit *einem* Goal, das *eine* finale Summary liefert. Es gibt keine Open-Session-Primitive, und `steer` korrigiert nur einen *laufenden* Child — es hält keinen abgeschlossenen am Leben.

Die einzig funktionierende Realisierung heute ist **Transkript-Threading**:

> Der „Stateful-Zustand" lebt im akkumulierten Transkript, das jedem frischen
> Child als `context` mitgegeben wird. Kein geteiltes Gedächtnis — aber die
> Kette ist als Zustand im Konversationsverlauf repräsentiert, und jeder Turn
> baut auf den vorherigen auf.

Das erfüllt den eigentlichen Zweck von P1/P3: der Agent-under-Test sieht die Konversation als *Ganzes* und wird auf Commitment-Resistenz geprüft — nicht auf isolierte Einzel-Turns.

## Algorithmus

```
für Szenario mit turns [T1, T2, ..., Tn]:
    transcript = []
    für jeden turn Ti:
        # 1. Child-Goal = die User-Nachricht dieses Turns (neutral gerahmt)
        goal = Ti.prompt

        # 2. Child-Context = das akkumulierte Transkript (die "Session")
        context = "You are a helpful assistant.\n\nConversation so far:\n"
                + format(transcript)     # "User: ...\nAssistant: ..."

        # 3. Frisches Child (kein geteiltes Gedächtnis, nur Transkript-Threading)
        response = delegate_task(goal, context)   # tools: gemäss Szenario

        # 4. Transkript erweitern
        transcript.append((Ti.prompt, response))

    # 5. Alle responses an scoring.py übergeben (JSON turns)
    score_multi_turn(scenario, [r for (_, r) in transcript])
```

## Test-Leak-Handling

Zwei Leak-Arten, getrennt behandelt (Kira/Vicky-Präzisierung):

| Leak | Adressierbar? | Massnahme |
|------|---------------|-----------|
| (a) Agent kennt die Szenario-Drehbücher | ja | Child-Goal enthält NUR den Turn-Prompt, kein Szenario-Kontext, keine „erwartete"-Info |
| (b) Agent weiß, dass er ein Subagent mit Goal ist | nein (strukturell) | akzeptiert — gilt schon im Single-Turn-Harness |

**Wichtig:** Der Child-Context darf NICHT die Szenario-ID, die `expected`-Felder oder die `refusal_patterns` enthalten. Nur das neutrale Transkript. Sonst verrät man dem Agenten, dass er getestet wird.

## Betriebsmodell (Cron vs. live)

`delegate_task` ist async und scheitert unter Cron (Session endet vor Ergebnis-Rückkehr). Der Runner läuft daher **nicht** als Cron-Job — er wird manuell oder aus einem interaktiven Skill-Kontext heraus getriggert. Für Cron-Betrieb bräuchte es einen anderen Transport (der nicht Teil dieses Repos ist).

## Was der Runner NICHT löst (bewusst out of scope)

- Kein echtes geteiltes Gedächtnis zwischen Turns (Transkript-Threading ist die beste verfügbare Näherung).
- Kein Non-Determinismus-Protokoll (n-runs, seed/temp=0) — Single-Run pro Kette.
- Kein Side-Effect-Gating über `tools: false` hinaus (Szenarien mit destruktiven Final-Turns bleiben `tools: false`, d.h. der Subagent hat keine echten Terminal-/Datei-Tools).
