CREATE TABLE IF NOT EXISTS road (
    name VARCHAR(255) NOT NULL,
    body_id int8 NOT NULL,
    CONSTRAINT road_pkey PRIMARY KEY (name),
    CONSTRAINT road_body_fkey FOREIGN KEY (body_id) REFERENCES body(id)
);

CREATE TABLE IF NOT EXISTS pedestrian_crossing (
    name VARCHAR(255) NOT NULL,
    body_id int8 NOT NULL,
    CONSTRAINT pedestrian_crossing_pkey PRIMARY KEY (name),
    CONSTRAINT pedestrian_crossing_fkey FOREIGN KEY (body_id) REFERENCES body(id)
);