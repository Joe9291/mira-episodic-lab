# Runde 4.3 - Joes Fallprüfung (5 Dev-Fälle nach Regel)

Bitte je Fall prüfen: Stimmt die Antwort des verdichteten Gedächtnisses mit dem vollen Gedächtnis überein (bzw. ist "compacted" richtig, weil die Frage einen gelöschten Zeitpunkt braucht)? Und ergibt die Antwort aus den Berichten Sinn?

## 1. Schnitt zwischen einem Bericht und seiner Korrektur

Welt dev-P3-00 A, Verzögerung 0, Schnitt nach Tag 9 (heute: Tag 12).

Relevante Berichte (alle):
- r00001 Tag 1: self (Rang 3) assert 'Brenna Quist' ab Tag 1 [the tiny violin / holder]
- r00002 Tag 7: Odile (Rang 2) assert 'Marit Drummet' ab Tag 5 [the tiny violin / holder]
- r00003 Tag 10: Odile (Rang 2) correct 'Juno Corland' -> r00002 [the tiny violin / holder]
- r00004 Tag 11: self (Rang 3) assert 'Ilsen Vesk' ab Tag 9 [the tiny violin / holder]

Verdichteter Stand C(9) - nur die noch geltenden Aussagen der gefragten Fakten:
- r00001: 'Brenna Quist' ab Tag 1, self (Rang 3), Ursprung o-r00001
- r00002: 'Marit Drummet' ab Tag 5, Odile (Rang 2), Ursprung o-r00002

Danach (Tail, relevante Berichte):
- r00003 Tag 10: Odile (Rang 2) correct 'Juno Corland' -> r00002 [the tiny violin / holder]
- r00004 Tag 11: self (Rang 3) assert 'Ilsen Vesk' ab Tag 9 [the tiny violin / holder]

Frage: {"op": "history", "now": 12}
- volles Gedächtnis M: `[{"valid_from": 1, "valid_to": 4, "status": "value", "value": "Brenna Quist", "ids": ["r00001"]}, {"valid_from": 5, "valid_to": 8, "status": "value", "value": "Juno Corland", "ids": ["r00003"]}, {"valid_from": 9, "valid_to": null, "status": "value", "value": "Ilsen Vesk", "ids": ["r00004"]}]`
- verdichtet (Mode T): `[{"valid_from": 1, "valid_to": 4, "status": "value", "value": "Brenna Quist", "ids": ["r00001"]}, {"valid_from": 5, "valid_to": 8, "status": "value", "value": "Juno Corland", "ids": ["r00003"]}, {"valid_from": 9, "valid_to": null, "status": "value", "value": "Ilsen Vesk", "ids": ["r00004"]}]`

## 2. Späte Nachricht, deren Gültigkeit vor dem Schnitt beginnt

Welt dev-P2-00 A, Verzögerung 0, Schnitt nach Tag 4 (heute: Tag 10).

Relevante Berichte (alle):
- r00001 Tag 1: self (Rang 3) assert 'Quarrel Library' ab Tag 1 [the silver basket / location]
- r00002 Tag 5: Yelda (Rang 2) assert 'Pellan Harbour' ab Tag 3 [the silver basket / location]
- r00003 Tag 9: self (Rang 3) assert 'Wyndle Forge' ab Tag 9 [the silver basket / location]

Verdichteter Stand C(4) - nur die noch geltenden Aussagen der gefragten Fakten:
- r00001: 'Quarrel Library' ab Tag 1, self (Rang 3), Ursprung o-r00001

Danach (Tail, relevante Berichte):
- r00002 Tag 5: Yelda (Rang 2) assert 'Pellan Harbour' ab Tag 3 [the silver basket / location]
- r00003 Tag 9: self (Rang 3) assert 'Wyndle Forge' ab Tag 9 [the silver basket / location]

Frage: {"op": "valid_at", "v": 3, "now": 10}
- volles Gedächtnis M: `{"status": "value", "value": "Pellan Harbour", "ids": ["r00002"]}`
- verdichtet (Mode T): `{"status": "value", "value": "Pellan Harbour", "ids": ["r00002"]}`

## 3. Konflikt vor dem Schnitt, aufgelöst danach

Welt dev-P8-00 A, Verzögerung 0, Schnitt nach Tag 8 (heute: Tag 10).

Relevante Berichte (alle):
- r00001 Tag 2: self (Rang 3) assert 'Yelda Brack' ab Tag 2 [the silver kettle / holder]
- r00002 Tag 5: Brenna (Rang 2) assert 'Quillon Ambery' ab Tag 4 [the silver kettle / holder]
- r00003 Tag 6: Casimo (Rang 2) assert 'Gorvin Pellow' ab Tag 4 [the silver kettle / holder]
- r00004 Tag 9: self (Rang 3) assert 'Casimo Vesk' ab Tag 4 [the silver kettle / holder]

Verdichteter Stand C(8) - nur die noch geltenden Aussagen der gefragten Fakten:
- r00001: 'Yelda Brack' ab Tag 2, self (Rang 3), Ursprung o-r00001
- r00002: 'Quillon Ambery' ab Tag 4, Brenna (Rang 2), Ursprung o-r00002
- r00003: 'Gorvin Pellow' ab Tag 4, Casimo (Rang 2), Ursprung o-r00003

Danach (Tail, relevante Berichte):
- r00004 Tag 9: self (Rang 3) assert 'Casimo Vesk' ab Tag 4 [the silver kettle / holder]

Frage: {"op": "digest", "now": 10}
- volles Gedächtnis M: `{"schema": "episodic_lab.r43_digest.v1", "segments": [{"valid_from": 2, "valid_to": 3, "status": "value", "support": [{"value": "Yelda Brack", "claims": [{"id": "r00001", "value": "Yelda Brack", "valid_from": 2, "source": "self", "rank": 3, "origin": "o-r00001"}]}], "agree": [], "dissent": [], "value": "Yelda Brack", "independent_origins": [{"value": "Yelda Brack", "n": 1}]}, {"valid_from": 4, "valid_to": null, "status": "value", "support": [{"value": "Casimo Vesk", "claims": [{"id": "r00004", "value": "Casimo Vesk", "valid_from": 4, "source": "self", "rank": 3, "origin": "o-r00004"}]}], "agree": [], "dissent": [{"id": "r00002", "value": "Quillon Ambery", "valid_from": 4, "source": "Brenna", "rank": 2, "origin": "o-r00002"}, {"id": "r00003", "value": "Gorvin Pellow", "valid_from": 4, "source": "Casimo", "rank": 2, "origin": "o-r00003"}], "value": "Casimo Vesk", "independent_origins": [{"value": "Casimo Vesk", "n": 1}]}], "current": {"status": "value", "value": "Casimo Vesk", "ids": ["r00004"]}}`
- verdichtet (Mode T): `{"schema": "episodic_lab.r43_digest.v1", "segments": [{"valid_from": 2, "valid_to": 3, "status": "value", "support": [{"value": "Yelda Brack", "claims": [{"id": "r00001", "value": "Yelda Brack", "valid_from": 2, "source": "self", "rank": 3, "origin": "o-r00001"}]}], "agree": [], "dissent": [], "value": "Yelda Brack", "independent_origins": [{"value": "Yelda Brack", "n": 1}]}, {"valid_from": 4, "valid_to": null, "status": "value", "support": [{"value": "Casimo Vesk", "claims": [{"id": "r00004", "value": "Casimo Vesk", "valid_from": 4, "source": "self", "rank": 3, "origin": "o-r00004"}]}], "agree": [], "dissent": [{"id": "r00002", "value": "Quillon Ambery", "valid_from": 4, "source": "Brenna", "rank": 2, "origin": "o-r00002"}, {"id": "r00003", "value": "Gorvin Pellow", "valid_from": 4, "source": "Casimo", "rank": 2, "origin": "o-r00003"}], "value": "Casimo Vesk", "independent_origins": [{"value": "Casimo Vesk", "n": 1}]}], "current": {"status": "value", "value": "Casimo Vesk", "ids": ["r00004"]}}`

## 4. Frage 'vor dem Ereignis', Ereignis vor dem Schnitt

Welt dev-P9-00 A, Verzögerung 0, Schnitt nach Tag 14 (heute: Tag 20).

Relevante Berichte (alle):
- r00001 Tag 1: Fenwick (Rang 2) assert 'Quillon Vesk' ab Tag 1 [the wooden compass / holder]
- r00002 Tag 6: Fenwick (Rang 2) assert 'Yelda Drummet' ab Tag 5 [the wooden compass / holder]
- r00003 Tag 10: self (Rang 3) assert 'Juno Ostrin' ab Tag 10 [the wooden compass / holder]
- r00004 Tag 14: Fenwick (Rang 2) assert 'Marit Brack' ab Tag 14 [the wooden compass / holder]
- r00005 Tag 14: self (Rang 3) assert 13 ab Tag 0 [event:met Juno Ostrin at Brannick Orchard / day]
- r00006 Tag 19: self (Rang 3) assert 'Ilsen Corland' ab Tag 19 [the wooden compass / holder]

Verdichteter Stand C(14) - nur die noch geltenden Aussagen der gefragten Fakten:
- r00005: 13 ab Tag 0, self (Rang 3), Ursprung o-r00005
- r00001: 'Quillon Vesk' ab Tag 1, Fenwick (Rang 2), Ursprung o-r00001
- r00002: 'Yelda Drummet' ab Tag 5, Fenwick (Rang 2), Ursprung o-r00002
- r00003: 'Juno Ostrin' ab Tag 10, self (Rang 3), Ursprung o-r00003
- r00004: 'Marit Brack' ab Tag 14, Fenwick (Rang 2), Ursprung o-r00004

Danach (Tail, relevante Berichte):
- r00006 Tag 19: self (Rang 3) assert 'Ilsen Corland' ab Tag 19 [the wooden compass / holder]

Frage: {"op": "before", "anchor": "met Juno Ostrin at Brannick Orchard", "now": 20}
- volles Gedächtnis M: `{"status": "value", "value": "Juno Ostrin", "ids": ["r00003"]}`
- verdichtet (Mode T): `{"status": "value", "value": "Juno Ostrin", "ids": ["r00003"]}`

## 5. Antwort "compacted": die Frage braucht einen Wissensstand vor dem Schnitt

Welt dev-P1-00 A, Verzögerung 0, Schnitt nach Tag 4 (heute: Tag 12).

Relevante Berichte (alle):
- r00001 Tag 2: Tamric (Rang 2) assert 'Sorrow Bridge' ab Tag 2 [the copper telescope / location]
- r00002 Tag 3: Marit (Rang 1) assert 'Sorrow Bridge' ab Tag 2 [the copper telescope / location]
- r00003 Tag 6: self (Rang 3) assert 'Mossgate Forge' ab Tag 6 [the copper telescope / location]
- r00004 Tag 11: self (Rang 3) assert 'Carrow Garden' ab Tag 9 [the copper telescope / location]

Verdichteter Stand C(4) - nur die noch geltenden Aussagen der gefragten Fakten:
- r00001: 'Sorrow Bridge' ab Tag 2, Tamric (Rang 2), Ursprung o-r00001
- r00002: 'Sorrow Bridge' ab Tag 2, Marit (Rang 1), Ursprung o-r00001

Danach (Tail, relevante Berichte):
- r00003 Tag 6: self (Rang 3) assert 'Mossgate Forge' ab Tag 6 [the copper telescope / location]
- r00004 Tag 11: self (Rang 3) assert 'Carrow Garden' ab Tag 9 [the copper telescope / location]

Frage: {"op": "believed_at", "t": 3, "now": 12}
- volles Gedächtnis M: `{"status": "value", "value": "Sorrow Bridge", "ids": ["r00001"]}`
- verdichtet (Mode T): `{"status": "unknown", "reason": "compacted"}`

