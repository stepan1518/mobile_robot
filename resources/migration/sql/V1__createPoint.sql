CREATE TABLE IF NOT EXISTS point (
    id int8 GENERATED ALWAYS AS IDENTITY NOT NULL,
    x NUMERIC NOT NULL,
    y NUMERIC NOT NULL,
    CONSTRAINT point_pkey PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS edge (
    parent_id int8 NOT NULL,
    child_id int8 NOT NULL,
    CONSTRAINT edge_pkey PRIMARY KEY (parent_id, child_id),
    CONSTRAINT parent_id_point_fkey FOREIGN KEY (parent_id) REFERENCES point(id),
    CONSTRAINT child_id_edge_fkey FOREIGN KEY (child_id) REFERENCES point(id)
);