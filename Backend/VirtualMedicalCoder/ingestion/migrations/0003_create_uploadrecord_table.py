from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0002_alter_uploadrecord_file_url'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS ingestion_uploadrecord (
                    id bigserial PRIMARY KEY,
                    file_url varchar(1000) NOT NULL DEFAULT '',
                    file_type varchar(10) NOT NULL,
                    raw_text text NOT NULL DEFAULT '',
                    file_name varchar(255) NOT NULL DEFAULT '',
                    status varchar(20) NOT NULL DEFAULT 'pending',
                    extracted_text text NOT NULL DEFAULT '',
                    error_message text NOT NULL DEFAULT '',
                    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_id bigint NOT NULL REFERENCES accounts_user(id) DEFERRABLE INITIALLY DEFERRED
                );

                CREATE INDEX IF NOT EXISTS ingestion_uploadrecord_user_id_8d9a8f5f_idx
                    ON ingestion_uploadrecord (user_id);

                CREATE INDEX IF NOT EXISTS ingestion_uploadrecord_created_at_2d0d3e6f_idx
                    ON ingestion_uploadrecord (created_at DESC);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS ingestion_uploadrecord CASCADE;
            """,
        ),
    ]