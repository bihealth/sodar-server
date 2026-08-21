import { type StudyShortcutResponseBody } from '@/types.ts'
import { ASSAY_PATH } from '../testConstants.ts'

const assayUrlPrefix: string = 'https://davrods.local' + ASSAY_PATH + '/'
const sessionRenderPath: string =
  '/samplesheets/study/germline/render/igv/33333333-3333-3333-3333-333333333333'
const igvOpenUrlPrefix: string =
  'http://127.0.0.1:60151/load?genome=b37&merge=false&file='
const igvMergeUrlPrefix: string =
  'http://127.0.0.1:60151/load?genome=b37&merge=true&file='

export const studyShortcutResponse: StudyShortcutResponseBody = {
  title: 'Pedigree-Wise Links for 0814',
  data: {
    session: {
      title: 'IGV Session File',
      files: [
        {
          label: 'Download session file',
          url: sessionRenderPath,
          title: null,
          extra_links: [
            {
              label: 'Open session file in IGV (replace current)',
              icon: 'share-square-o',
              url: igvOpenUrlPrefix + encodeURIComponent(
                sessionRenderPath + '.xml')
            },
            {
              label: 'Merge into current IGV session',
              icon: 'plus',
              url: igvMergeUrlPrefix + encodeURIComponent(
                sessionRenderPath + '.xml')
            }
          ]
        }
      ]
    },
    bam: {
      title: 'BAM Files',
      files: [
        {
          label: '0814-N1-DNA1-WGS1',
          url: assayUrlPrefix + '0814-N1-DNA1-WGS1/test1.bam',
          title: 'Download BAM file',
          extra_links: [
            {
              label: 'Add BAM file to IGV',
              icon: 'plus',
              url: 'http://127.0.0.1:60151/load?merge=true&file=' +
                   assayUrlPrefix + '0814-N1-DNA1-WGS1/test1.bam'
            }
          ]
        }
      ],
      omit_info: '*dragen_evidence.bam'
    },
    vcf: {
      title: 'VCF Files',
      files: [
        {
          label: '0814-N1-DNA1-WGS1',
          url: assayUrlPrefix + '0814-N1-DNA1-WGS1/test1.vcf.gz',
          title: 'Download VCF file',
          extra_links: [
            {
              label: 'Add VCF file to IGV',
              icon: 'plus',
              url: 'http://127.0.0.1:60151/load?merge=true&file=' +
                   assayUrlPrefix + '0814-N1-DNA1-WGS1/test1.vcf.gz'
            }
          ]
        }
      ],
      omit_info: '*cnv.vcf.gz, *ploidy.vcf.gz, *sv.vcf.gz'
    }
  }
}
