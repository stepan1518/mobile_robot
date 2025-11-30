CREATE TABLE IF NOT EXISTS point (
    name VARCHAR(255) NOT NULL,
    x NUMERIC NOT NULL,
    y NUMERIC NOT NULL,
    CONSTRAINT point_pkey PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS edge (
    parent_id VARCHAR(255) NOT NULL,
    child_id VARCHAR(255) NOT NULL,
    CONSTRAINT edge_pkey PRIMARY KEY (parent_id, child_id),
    CONSTRAINT parent_id_point_fkey FOREIGN KEY (parent_id) REFERENCES point(name),
    CONSTRAINT child_id_edge_fkey FOREIGN KEY (child_id) REFERENCES point(name)
);