-- Add unique constraint to ic_specifications table
-- This constraint ensures the same IC from the same manufacturer isn't duplicated

ALTER TABLE ic_specifications 
ADD CONSTRAINT uq_ic_part_manufacturer 
UNIQUE (part_number, manufacturer);
