
CREATE SEQUENCE orderidseq OWNED BY placesorder.orderid;
SELECT SETVAL('orderidseq', (select max(orderid)+1 from placesorder), false);
ALTER TABLE placesorder ALTER COLUMN orderid SET DEFAULT nextval('orderidseq');