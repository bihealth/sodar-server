export const PROJECT_UUID: string = '00000000-0000-0000-0000-000000000000'
export const STUDY_UUID: string = '11111111-1111-1111-1111-111111111111'
export const ASSAY_UUID: string = '22222222-2222-2222-2222-222222222222'
export const USER_UUID: string = '66666666-6666-6666-6666-666666666666'
export const USER_UUID2: string = '77777777-7777-7777-7777-777777777777'

export const PROJECT_SAMPLE_PATH: string = '/sodarZone/projects/00/' +
  PROJECT_UUID + '/sample_data'

export const STUDY_PATH: string = '/sodarZone/projects/00/' +
  PROJECT_UUID + '/sample_data/study_' + STUDY_UUID
export const ASSAY_PATH: string = STUDY_PATH + '/' + 'assay_' + ASSAY_UUID
export const ASSAY_PATH_PREFIX: string = ASSAY_PATH + '/'

export const STUDY_PLUGIN_NAME: string = 'samplesheets_study_germline'
export const STUDY_PLUGIN_TITLE: string = 'Sample Sheets Germline Study Plugin'

export const ASSAY_PLUGIN_NAME: string = 'samplesheets_assay_dna_sequencing'
export const ASSAY_PLUGIN_TITLE: string = 'DNA Sequencing Assay Plugin'

export const MISC_FILES_DIR: string = 'MiscFiles'
