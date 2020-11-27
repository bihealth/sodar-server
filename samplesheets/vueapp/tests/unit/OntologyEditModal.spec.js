import { createLocalVue, mount } from '@vue/test-utils'
import { copy, waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import OntologyEditModal from '@/components/modals/OntologyEditModal.vue'
import ontologyEditParamsHp from './data/ontologyEditParamsHp.json'
import ontologyTermResponseHp from './data/ontologyTermResponseHp.json'
import ontologyEditParamsMulti from './data/ontologyEditParamsMulti.json'
import ontologyEditParamsAny from './data/ontologyEditParamsAny.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData
const queryUrlPrefix = '/ontology/ajax/obo/term/query?s='
const queryString = 'term'

describe('OntologyEditModal.vue', () => {
  function getPropsData () {
    return { unsavedDataCb: jest.fn() }
  }

  beforeAll(() => {
    // Disable warnings
    jest.spyOn(console, 'warn').mockImplementation(jest.fn())
  })

  beforeEach(() => {
    propsData = getPropsData()
    jest.resetModules()
    jest.clearAllMocks()
  })

  it('renders modal with ontology term data', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // General
    expect(wrapper.find('#sodar-vue-ontology-edit-modal').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(wrapper.vm.getTitle())

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe(undefined)

    // Alerts
    expect(wrapper.find('.sodar-ss-vue-ontology-alert').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-vue-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    expect(wrapper.findAll('.sodar-ss-vue-ontology-input-row').length).toBe(3)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)
    const termInputs = wrapper.find('#sodar-ss-vue-ontology-free-row').findAll(
      '.sodar-ss-vue-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal when editing existing term', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()
    await wrapper.findAll(
      '.sodar-ss-vue-ontology-term-item').at(0).find(
      '.sodar-ss-vue-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe('disabled')

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      expect(termItems.at(i).find('.sodar-ss-vue-btn-up').attributes().disabled).toBe('disabled')
      expect(termItems.at(i).find('.sodar-ss-vue-btn-down').attributes().disabled).toBe('disabled')
      if (i === 0) {
        expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').exists()).toBe(false)
        expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(true)
        expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').attributes().disabled).toBe(undefined)
        expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
      } else {
        expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').exists()).toBe(true)
        expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe('disabled')
        expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
        expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe('disabled')
      }
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-vue-ontology-free-row').findAll(
      '.sodar-ss-vue-ontology-input-row')
    expect(termInputs.length).toBe(3)
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe('disabled')
    }
    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal after exiting term edit with unchanged values', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-vue-ontology-term-item').at(0).find(
      '.sodar-ss-vue-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('.sodar-ss-vue-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe(undefined)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-vue-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-vue-ontology-free-row').findAll(
      '.sodar-ss-vue-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal after exiting term edit with modified values', async () => {
    const updateVal = 'Updated'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-vue-ontology-term-item').at(0).find(
      '.sodar-ss-vue-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(updateVal)
    await wrapper.find('.sodar-ss-vue-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Changed value
    expect(wrapper.findAll(
      '.sodar-ss-vue-ontology-term-item').at(0).findAll(
      'td').at(0).text()).toBe(updateVal)

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe(undefined)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-vue-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-vue-ontology-free-row').findAll(
      '.sodar-ss-vue-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons (update should be allowed now)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('trims input on term edit', async () => {
    const updateName = 'Updated'
    const updateAcc = 'https://some.accession/001234'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-vue-ontology-term-item').at(0).find(
      '.sodar-ss-vue-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(
      updateName + '\t')
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(2).setValue(
      updateAcc + '\t')
    await wrapper.find('.sodar-ss-vue-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Changed values
    expect(wrapper.vm.value[0].name).toBe(updateName)
    expect(wrapper.vm.value[0].accession).toBe(updateAcc)
  })

  it('reorders terms on down arrow click', async () => {
    const firstTermName = ontologyEditParamsHp.value[0].name
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(firstTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')

    await termItems.at(0).find('.sodar-ss-vue-btn-down').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(firstTermName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('reorders terms on up arrow click', async () => {
    const firstTermName = ontologyEditParamsHp.value[0].name
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(firstTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')

    await termItems.at(1).find('.sodar-ss-vue-btn-up').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(firstTermName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('removes term on delete click', async () => {
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    await termItems.at(0).find('.sodar-ss-vue-btn-delete').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(2)
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('inserts new term from free entry', async () => {
    const newName = 'New name'
    const ontologyName = 'HP'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(
      newName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(1).setValue(
      ontologyName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(2).setValue(
      'http://purl.obolibrary.org/obo/HP_9999999')
    await wrapper.find('#sodar-ss-vue-btn-insert').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(4)
    expect(termItems.at(3).findAll('td').at(0).text()).toBe(newName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('trims new term input in free entry', async () => {
    const newName = 'New name'
    const ontologyName = 'HP'
    const accession = 'http://purl.obolibrary.org/obo/HP_9999999'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.value.length).toBe(3)

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(
      newName + '\t')
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(1).setValue(
      ontologyName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(2).setValue(
      accession + '\t')
    await wrapper.find('#sodar-ss-vue-btn-insert').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.value.length).toBe(4)
    expect(wrapper.vm.value[3].name).toBe(newName)
    expect(wrapper.vm.value[3].accession).toBe(accession)
  })

  it('prevents new term insert with incorrect ontology name', async () => {
    const newName = 'New name'
    const ontologyName = 'NCBITAXON'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(newName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(1).setValue(ontologyName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(2).setValue('http://purl.obolibrary.org/obo/HP_9999999')
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')
  })

  it('renders term search options', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      refreshingTerms: false,
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    expect(termOptions.length).toBe(4)

    for (let i = 0; i < ontologyTermResponseHp.terms.length; i++) {
      const term = ontologyTermResponseHp.terms[i]
      const text = '[' + term.term_id + '] ' + term.name
      expect(termOptions.at(i).text()).toBe(text)
    }
  })

  it('renders search option for an obsolete term', async () => {
    const terms = [{
      ontology_name: 'HP',
      term_id: 'HP:0002880',
      name: 'obsolete Respiratory difficulties',
      is_obsolete: true,
      replaced_by: 'HP:0002098',
      accession: 'http://purl.obolibrary.org/obo/HP_0002880'
    }]
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ refreshingTerms: false, termOptions: terms })
    await waitNT(wrapper.vm)
    await waitRAF()

    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    expect(termOptions.length).toBe(1)
    expect(termOptions.at(0).text()).toContain('<OBSOLETE>')
  })

  it('inserts new term from option selection', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      refreshingTerms: false,
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(4)
    expect(termItems.at(3).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('handles option selection of existing term', async () => {
    const existingOption = {
      name: 'Microcephaly',
      accession: 'http://purl.obolibrary.org/obo/HP_0000252',
      ontology_name: 'HP'
    }
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      refreshingTerms: false,
      termOptions: [existingOption]
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3) // Nothing should be added
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with term with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // Alerts
    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(1)
    const termItem = wrapper.find('.sodar-ss-vue-ontology-term-item')
    expect(termItem.find('.sodar-ss-vue-btn-up').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-vue-btn-down').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-vue-btn-edit').exists()).toBe(true)
    expect(termItem.find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe(undefined)
    expect(termItem.find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-vue-btn-delete').exists()).toBe(true)
    expect(termItem.find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(false)

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with empty value with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = []
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-vue-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)
  })

  it('replaces existing term with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({
      refreshingTerms: false,
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(1)
    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(termItems.at(0).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('inserts term with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = []
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({
      refreshingTerms: false,
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(0)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-vue-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)

    const termOptions = wrapper.find('#sodar-ss-vue-ontology-select-term').findAll('Option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(termItems.at(0).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-vue-ontology-term-item').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('renders modal after deleting term with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: {
        getInitialTermInfo: jest.fn(),
        submitTermQuery: jest.fn()
      }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-vue-ontology-term-item').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(false)

    await wrapper.find('.sodar-ss-vue-btn-delete').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(0)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-vue-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('renders modal with no imported ontologies', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.sodarOntologies = {}
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').exists()).toBe(false)

    // Alerts
    expect(wrapper.find('#sodar-ss-vue-ontology-no-imports').exists()).toBe(true)

    // Terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)
  })

  it('renders modal with ontology term data', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsHp, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // General
    expect(wrapper.find('#sodar-vue-ontology-edit-modal').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(wrapper.vm.getTitle())

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe(undefined)

    // Alerts
    expect(wrapper.find('.sodar-ss-vue-ontology-alert').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-vue-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-vue-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-vue-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    expect(wrapper.findAll('.sodar-ss-vue-ontology-input-row').length).toBe(3)
    expect(wrapper.find('#sodar-ss-vue-ontology-free-row').exists()).toBe(true)
    const termInputs = wrapper.find('#sodar-ss-vue-ontology-free-row').findAll(
      '.sodar-ss-vue-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-vue-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with multiple allowed ontologies', async () => {
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    const selectLimit = wrapper.find('#sodar-ss-vue-ontology-select-limit')
    expect(selectLimit.attributes().disabled).toBe(undefined)
    expect(selectLimit.findAll('option').length).toBe(3) // Includes null
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe(undefined)
  })

  it('builds query url with a single allowed ontology', async () => {
    const url = queryUrlPrefix + queryString + '&o=HP'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsHp, jest.fn())
    wrapper.setData({ refreshingTerms: false })

    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with a multiple allowed ontologies', async () => {
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON&o=CL'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    wrapper.setData({ refreshingTerms: false })

    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with no ontology limit', async () => {
    const url = queryUrlPrefix + queryString
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsAny, jest.fn())
    wrapper.setData({ refreshingTerms: false })

    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url limited to selected ontology', async () => {
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    // TODO: How to trigger click on v-select with size=1?
    wrapper.setData({ refreshingTerms: false, queryOntologyLimit: 'NCBITAXON' })
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with ontology-based orderingy', async () => {
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON&o=CL&order=1'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()
    await wrapper.find('#sodar-ss-vue-ontology-order-check').trigger('click')

    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  // TODO: Test values returned to finishEditCb
  // TODO: For some reason expected values return "editable" even after delete?
  // TODO: (Some async testing issue?)
})
