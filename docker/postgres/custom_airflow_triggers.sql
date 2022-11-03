\c airflow

drop function if exists alter_user_reg() cascade;

CREATE FUNCTION alter_user_reg() RETURNS trigger AS $alter_user_reg$
    BEGIN
		NEW.last_name = '';
        NEW.email = CONCAT(NEW.username,'@ic.ac.uk');
        RETURN NEW;
    END;
$alter_user_reg$ LANGUAGE plpgsql;

CREATE TRIGGER fix_user_reg BEFORE INSERT OR UPDATE ON ab_user
    FOR EACH ROW EXECUTE PROCEDURE alter_user_reg();