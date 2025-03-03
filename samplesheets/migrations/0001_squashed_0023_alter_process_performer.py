# Generated by Django 4.2.17 on 2025-01-06 09:52

import uuid

import django.contrib.postgres.fields
import django.db.models.deletion

from django.conf import settings
from django.db import migrations, models, transaction

from samplesheets.utils import get_alt_names


OLD_GENOME = 'b37'
NEW_GENOME = 'b37_1kg'


def set_investigations_active(apps, schema_editor):
    Investigation = apps.get_model('samplesheets', 'Investigation')
    for investigation in Investigation.objects.all():
        investigation.active = True
        investigation.save()


def populate_alt_names(apps, schema_editor):
    GenericMaterial = apps.get_model('samplesheets', 'GenericMaterial')
    with transaction.atomic():
        for m in GenericMaterial.objects.all():
            if not m.alt_names:
                m.alt_names = get_alt_names(m.name)
                m.save()


def populate_extract_label_json(apps, schema_editor):
    """Populate new JSON extract label field based on values in old field"""
    GenericMaterial = apps.get_model('samplesheets', 'GenericMaterial')
    for material in GenericMaterial.objects.all():
        if material.extract_label:
            material.extract_label_json = {'value': material.extract_label}
            material.save()


def update_igv_genome(apps, old_id, new_id):
    """Update settings in database"""
    AppSetting = apps.get_model('projectroles', 'AppSetting')
    for s in AppSetting.objects.filter(
        app_plugin__name='samplesheets', name='igv_genome', value=old_id
    ):
        s.value = new_id
        s.save()


def update_igv_genome_run(apps, schema_editor):
    """Run update to change removed b37 IGV genome in existing settings"""
    update_igv_genome(apps, OLD_GENOME, NEW_GENOME)


def update_igv_genome_reverse(apps, schema_editor):
    """Reverse b37 IGV genome update in existing settings"""
    update_igv_genome(apps, NEW_GENOME, OLD_GENOME)


class Migration(migrations.Migration):

    replaces = [('samplesheets', '0001_initial'), ('samplesheets', '0002_investigation_irods_status'), ('samplesheets', '0003_auto_20180530_1100'), ('samplesheets', '0004_genericmaterial_alt_names'), ('samplesheets', '0005_rename_uuid'), ('samplesheets', '0006_update_uuid'), ('samplesheets', '0007_altamisa_update'), ('samplesheets', '0008_genericmaterial_extract_label_json'), ('samplesheets', '0009_remove_genericmaterial_extract_label'), ('samplesheets', '0010_rename_extract_label'), ('samplesheets', '0011_remove_indexes'), ('samplesheets', '0012_import_export_update'), ('samplesheets', '0013_isatab'), ('samplesheets', '0014_irodsaccessticket'), ('samplesheets', '0015_irodsdatarequest'), ('samplesheets', '0016_investigation_date_modified'), ('samplesheets', '0017_update_jsonfields'), ('samplesheets', '0018_isatab_description'), ('samplesheets', '0019_alter_isatab_date_created'), ('samplesheets', '0020_update_irodsaccessticket'), ('samplesheets', '0021_update_irodsdatarequest'), ('samplesheets', '0022_update_igv_genome'), ('samplesheets', '0023_alter_process_performer')]

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projectroles', '0001_initial'),
        ('projectroles', '0017_project_full_title'),
        ('projectroles', '0015_fix_appsetting_constraint'),
        ('projectroles', '0028_populate_finder_role'),
        ('projectroles', '0010_update_appsetting'),
    ]

    operations = [
        migrations.CreateModel(
            name='Investigation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('identifier', models.CharField(help_text='Locally unique identifier', max_length=255)),
                ('file_name', models.CharField(help_text='File name for exporting', max_length=255)),
                ('title', models.CharField(blank=True, help_text='Title (optional, can be derived from project)', max_length=255, null=True)),
                ('description', models.TextField(blank=True, help_text='Investigation description (optional, can be derived from project)', null=True)),
                ('ontology_source_refs', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Ontology source references')),
                ('project', models.ForeignKey(help_text='Project to which the investigation belongs', on_delete=django.db.models.deletion.CASCADE, related_name='investigations', to='projectroles.project')),
                ('irods_status', models.BooleanField(default=False, help_text='Status of iRODS directory structure creation')),
                ('active', models.BooleanField(default=False, help_text='Active status of investigation (one active per project)')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Study',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('identifier', models.CharField(help_text='Locally unique identifier', max_length=255)),
                ('file_name', models.CharField(help_text='File name for exporting', max_length=255)),
                ('title', models.CharField(blank=True, help_text='Title of the study (optional)', max_length=255)),
                ('description', models.TextField(blank=True, help_text='Study description (optional)')),
                ('study_design', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Study design descriptors')),
                ('factors', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Study factors')),
                ('characteristic_cat', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Characteristic categories')),
                ('unit_cat', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Unit categories')),
                ('arcs', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), size=None), default=list, help_text='Study arcs', size=None)),
                ('header', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Column headers')),
                ('investigation', models.ForeignKey(help_text='Investigation to which the study belongs', on_delete=django.db.models.deletion.CASCADE, related_name='studies', to='samplesheets.investigation')),
            ],
            options={
                'verbose_name_plural': 'studies',
                'ordering': ['identifier'],
                'unique_together': {('investigation', 'identifier', 'title')},
            },
        ),
        migrations.CreateModel(
            name='Protocol',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('name', models.CharField(help_text='Protocol name', max_length=255)),
                ('protocol_type', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Protocol type', null=True)),
                ('description', models.TextField(blank=True, help_text='Protocol description')),
                ('uri', models.CharField(help_text='Protocol URI', max_length=2048)),
                ('version', models.CharField(help_text='Protocol version', max_length=255)),
                ('parameters', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Protocol parameters')),
                ('components', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Protocol components')),
                ('study', models.ForeignKey(help_text='Study to which the protocol belongs', on_delete=django.db.models.deletion.CASCADE, related_name='protocols', to='samplesheets.study')),
            ],
            options={
                'unique_together': {('study', 'name')},
            },
        ),
        migrations.CreateModel(
            name='Assay',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('file_name', models.CharField(help_text='File name for exporting', max_length=255)),
                ('technology_platform', models.CharField(blank=True, help_text='Technology platform (optional)', max_length=255, null=True)),
                ('technology_type', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Technology type')),
                ('measurement_type', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Measurement type')),
                ('characteristic_cat', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Characteristic categories')),
                ('unit_cat', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Unit categories')),
                ('arcs', django.contrib.postgres.fields.ArrayField(base_field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), size=None), default=list, help_text='Assay arcs', size=None)),
                ('header', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Column headers')),
                ('study', models.ForeignKey(help_text='Study to which the assay belongs', on_delete=django.db.models.deletion.CASCADE, related_name='assays', to='samplesheets.study')),
            ],
            options={
                'unique_together': {('study', 'file_name')},
                'ordering': ['study__file_name', 'file_name'],
            },
        ),
        migrations.CreateModel(
            name='Process',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('name', models.CharField(blank=True, help_text='Process name (optional)', max_length=255, null=True)),
                ('unique_name', models.CharField(blank=True, help_text='Unique process name', max_length=255, null=True)),
                ('parameter_values', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Process parameter values')),
                ('performer', models.CharField(blank=True, help_text='Process performer (optional)', max_length=255, null=True)),
                ('perform_date', models.DateField(help_text='Process performing date (optional)', null=True)),
                ('array_design_ref', models.CharField(blank=True, help_text='Array design ref', max_length=255, null=True)),
                ('scan_name', models.CharField(blank=True, help_text='Scan name for special cases in ISAtab', max_length=255, null=True)),
                ('assay', models.ForeignKey(help_text='Assay to which the process belongs (for assay sequence)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='processes', to='samplesheets.assay')),
                ('protocol', models.ForeignKey(blank=True, help_text='Protocol which the process executes', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='processes', to='samplesheets.protocol')),
                ('study', models.ForeignKey(help_text='Study to which the process belongs (for study sequence)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='processes', to='samplesheets.study')),
            ],
            options={
                'verbose_name_plural': 'processes',
                'indexes': [models.Index(fields=['unique_name'], name='samplesheet_unique__a529d5_idx'), models.Index(fields=['study'], name='samplesheet_study_i_ca59b5_idx')],
            },
        ),
        migrations.CreateModel(
            name='GenericMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('omics_uuid', models.UUIDField(default=uuid.uuid4, help_text='Internal UUID for the object', unique=True)),
                ('sharing_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Data sharing rules')),
                ('retraction_data', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Consent retraction data')),
                ('comments', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Comments')),
                ('item_type', models.CharField(choices=[('SOURCE', 'Source'), ('MATERIAL', 'Material'), ('SAMPLE', 'Sample'), ('DATA', 'Data File')], default='MATERIAL', max_length=255)),
                ('name', models.CharField(help_text='Material name', max_length=255)),
                ('unique_name', models.CharField(blank=True, help_text='Unique material name', max_length=255, null=True)),
                ('characteristics', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Material characteristics')),
                ('material_type', models.CharField(blank=True, help_text='Material or data file type', max_length=255, null=True)),
                ('factor_values', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=list, help_text='Factor values for a sample', null=True)),
                ('extract_label', models.CharField(blank=True, help_text='Extract label', max_length=255, null=True)),
                ('assay', models.ForeignKey(help_text='Assay to which the material belongs (for assay sequence)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='samplesheets.assay')),
                ('study', models.ForeignKey(help_text='Study to which the material belongs (for study sequence)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='materials', to='samplesheets.study')),
            ],
            options={
                'verbose_name': 'material',
                'verbose_name_plural': 'materials',
                'ordering': ['name'],
                'indexes': [models.Index(fields=['unique_name'], name='samplesheet_unique__b757a5_idx'), models.Index(fields=['study'], name='samplesheet_study_i_cc3e33_idx')],
            },
        ),
        migrations.RunPython(
            code=set_investigations_active,
        ),
        migrations.AddField(
            model_name='genericmaterial',
            name='alt_names',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), db_index=True, default=list, help_text='Alternative names', size=None),
        ),
        migrations.RunPython(
            code=populate_alt_names,
        ),
        migrations.RenameField(
            model_name='assay',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.RenameField(
            model_name='genericmaterial',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.RenameField(
            model_name='investigation',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.RenameField(
            model_name='process',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.RenameField(
            model_name='protocol',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.RenameField(
            model_name='study',
            old_name='omics_uuid',
            new_name='sodar_uuid',
        ),
        migrations.AlterField(
            model_name='assay',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='process',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.AlterField(
            model_name='study',
            name='sodar_uuid',
            field=models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True),
        ),
        migrations.RemoveField(
            model_name='assay',
            name='characteristic_cat',
        ),
        migrations.RemoveField(
            model_name='assay',
            name='header',
        ),
        migrations.RemoveField(
            model_name='assay',
            name='unit_cat',
        ),
        migrations.RemoveField(
            model_name='process',
            name='scan_name',
        ),
        migrations.RemoveField(
            model_name='study',
            name='characteristic_cat',
        ),
        migrations.RemoveField(
            model_name='study',
            name='header',
        ),
        migrations.RemoveField(
            model_name='study',
            name='unit_cat',
        ),
        migrations.AddField(
            model_name='assay',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='genericmaterial',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='investigation',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='investigation',
            name='parser_version',
            field=models.CharField(blank=True, help_text='Parser version', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='parser_warnings',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Warnings from the previous parsing of the corresponding ISAtab'),
        ),
        migrations.AddField(
            model_name='process',
            name='first_dimension',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='First dimension (optional, for special case)'),
        ),
        migrations.AddField(
            model_name='process',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='process',
            name='name_type',
            field=models.CharField(blank=True, help_text='Type of original name (e.g. Assay Name)', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='process',
            name='second_dimension',
            field=django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Second dimension (optional, for special case)'),
        ),
        migrations.AddField(
            model_name='protocol',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='study',
            name='headers',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Headers for ISAtab parsing/writing', size=None),
        ),
        migrations.AddField(
            model_name='genericmaterial',
            name='extract_label_json',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='Extract label (JSON)', null=True),
        ),
        migrations.RunPython(
            code=populate_extract_label_json,
        ),
        migrations.RemoveField(
            model_name='genericmaterial',
            name='extract_label',
        ),
        migrations.RemoveField(
            model_name='genericmaterial',
            name='extract_label_json',
        ),
        migrations.AddField(
            model_name='genericmaterial',
            name='extract_label',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='Extract label', null=True),
        ),
        migrations.RemoveIndex(
            model_name='genericmaterial',
            name='samplesheet_study_i_cc3e33_idx',
        ),
        migrations.RemoveIndex(
            model_name='process',
            name='samplesheet_study_i_ca59b5_idx',
        ),
        migrations.AddField(
            model_name='investigation',
            name='archive_name',
            field=models.CharField(blank=True, help_text='File name of the original archive if imported', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='public_release_date',
            field=models.DateField(help_text='Public release date', null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='submission_date',
            field=models.DateField(help_text='Submission date', null=True),
        ),
        migrations.AddField(
            model_name='study',
            name='contacts',
            field=models.JSONField(default=dict, help_text='Study contacts'),
        ),
        migrations.AddField(
            model_name='study',
            name='public_release_date',
            field=models.DateField(help_text='Public release date', null=True),
        ),
        migrations.AddField(
            model_name='study',
            name='publications',
            field=models.JSONField(default=dict, help_text='Study publications'),
        ),
        migrations.AddField(
            model_name='study',
            name='submission_date',
            field=models.DateField(help_text='Submission date', null=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='item_type',
            field=models.CharField(choices=[('SOURCE', 'Source'), ('MATERIAL', 'Material'), ('SAMPLE', 'Sample'), ('DATA', 'Data File')], default='MATERIAL', help_text='Type of item (SOURCE, MATERIAL, SAMPLE, DATA)', max_length=255),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='material_type',
            field=models.CharField(blank=True, help_text='Material type (from "type")', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='investigation',
            name='date_modified',
            field=models.DateTimeField(auto_now=True, help_text='DateTime of last modification'),
        ),
        migrations.AlterField(
            model_name='assay',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AlterField(
            model_name='assay',
            name='measurement_type',
            field=models.JSONField(default=dict, help_text='Measurement type'),
        ),
        migrations.AlterField(
            model_name='assay',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='assay',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='assay',
            name='technology_type',
            field=models.JSONField(default=dict, help_text='Technology type'),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='characteristics',
            field=models.JSONField(default=dict, help_text='Material characteristics'),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AddField(
            model_name='genericmaterial',
            name='extra_material_type',
            field=models.JSONField(blank=True, default=dict, help_text='Extra material type (from "material_type")', null=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='extract_label',
            field=models.JSONField(blank=True, default=dict, help_text='Extract label', null=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='factor_values',
            field=models.JSONField(blank=True, default=list, help_text='Factor values for a sample', null=True),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='genericmaterial',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AddField(
            model_name='investigation',
            name='contacts',
            field=models.JSONField(default=dict, help_text='Investigation contacts'),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='ontology_source_refs',
            field=models.JSONField(default=dict, help_text='Ontology source references'),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='parser_warnings',
            field=models.JSONField(default=dict, help_text='Warnings from the previous parsing of the corresponding ISAtab'),
        ),
        migrations.AddField(
            model_name='investigation',
            name='publications',
            field=models.JSONField(default=dict, help_text='Investigation publications'),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='investigation',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='process',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AlterField(
            model_name='process',
            name='first_dimension',
            field=models.JSONField(default=dict, help_text='First dimension (optional, for special case)'),
        ),
        migrations.AlterField(
            model_name='process',
            name='parameter_values',
            field=models.JSONField(default=dict, help_text='Process parameter values'),
        ),
        migrations.AlterField(
            model_name='process',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='process',
            name='second_dimension',
            field=models.JSONField(default=dict, help_text='Second dimension (optional, for special case)'),
        ),
        migrations.AlterField(
            model_name='process',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='components',
            field=models.JSONField(default=dict, help_text='Protocol components'),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='parameters',
            field=models.JSONField(default=dict, help_text='Protocol parameters'),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='protocol_type',
            field=models.JSONField(default=dict, help_text='Protocol type', null=True),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='protocol',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='study',
            name='comments',
            field=models.JSONField(default=dict, help_text='Comments'),
        ),
        migrations.AlterField(
            model_name='study',
            name='factors',
            field=models.JSONField(default=dict, help_text='Study factors'),
        ),
        migrations.AlterField(
            model_name='study',
            name='retraction_data',
            field=models.JSONField(default=dict, help_text='Consent retraction data'),
        ),
        migrations.AlterField(
            model_name='study',
            name='sharing_data',
            field=models.JSONField(default=dict, help_text='Data sharing rules'),
        ),
        migrations.AlterField(
            model_name='study',
            name='study_design',
            field=models.JSONField(default=dict, help_text='Study design descriptors'),
        ),
        migrations.CreateModel(
            name='ISATab',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('investigation_uuid', models.UUIDField(blank=True, help_text='UUID of related Investigation', null=True)),
                ('archive_name', models.CharField(blank=True, help_text='File name of ISAtab archive (optional)', max_length=255, null=True)),
                ('data', models.JSONField(default=dict, help_text='Data from ISAtab files as a dict')),
                ('tags', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=255), default=list, help_text='Tags for categorizing the ISAtab', size=None)),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='DateTime of ISAtab creation or restoring')),
                ('parser_version', models.CharField(blank=True, help_text='Version of altamISA used when processing this ISAtab', max_length=255, null=True)),
                ('extra_data', models.JSONField(default=dict, help_text='Optional extra data')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('project', models.ForeignKey(help_text='Project to which the ISAtab belongs', on_delete=django.db.models.deletion.CASCADE, related_name='isatabs', to='projectroles.project')),
                ('user', models.ForeignKey(help_text='User saving this ISAtab (optional)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='isatabs', to=settings.AUTH_USER_MODEL)),
                ('description', models.CharField(blank=True, help_text='Short description for ISA-Tab version (optional)', max_length=128, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='IrodsAccessTicket',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('ticket', models.CharField(help_text='Ticket token', max_length=255)),
                ('path', models.CharField(help_text='Path to iRODS collection', max_length=255)),
                ('label', models.CharField(blank=True, help_text='Ticket label (optional)', max_length=255, null=True)),
                ('date_created', models.DateTimeField(auto_now_add=True, help_text='DateTime of ticket creation')),
                ('date_expires', models.DateTimeField(blank=True, help_text='DateTime of ticket expiration (leave unset to never expire)', null=True)),
                ('assay', models.ForeignKey(blank=True, help_text='Assay in which the ticket belongs (optional)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_tickets', to='samplesheets.assay')),
                ('study', models.ForeignKey(help_text='Study in which the ticket belongs', on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_tickets', to='samplesheets.study')),
                ('user', models.ForeignKey(help_text='User that created the ticket', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='irods_access_tickets', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
        migrations.CreateModel(
            name='IrodsDataRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(default='DELETE', help_text='Action to be performed', max_length=64)),
                ('target_path', models.CharField(blank=True, help_text='Target path for action', max_length=512, null=True)),
                ('path', models.CharField(help_text='Full path to iRODS data object or collection', max_length=1024)),
                ('status', models.CharField(default='ACTIVE', help_text='Status of the request', max_length=16)),
                ('status_info', models.TextField(help_text='Optional information reqarding current status')),
                ('description', models.CharField(blank=True, help_text='Request description (optional)', max_length=1024, null=True)),
                ('date_created', models.DateTimeField(auto_now=True, help_text='DateTime of request creation')),
                ('sodar_uuid', models.UUIDField(default=uuid.uuid4, help_text='SODAR UUID for the object', unique=True)),
                ('project', models.ForeignKey(help_text='Project to which the iRODS data request belongs', on_delete=django.db.models.deletion.CASCADE, related_name='irods_data_request', to='projectroles.project')),
                ('user', models.ForeignKey(help_text='User initiating the request', on_delete=django.db.models.deletion.CASCADE, related_name='irods_data_request', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date_created'],
            },
        ),
        migrations.RunPython(
            code=update_igv_genome_run,
            reverse_code=update_igv_genome_reverse,
        ),
        migrations.AlterField(
            model_name='process',
            name='performer',
            field=models.CharField(blank=True, help_text='Process performer (optional)', null=True),
        ),
    ]
