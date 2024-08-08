import { createLocalVue, mount } from '@vue/test-utils'
import { copy, waitNT, waitRAF } from '../testUtils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import OntologyEditModal from '@/components/modals/OntologyEditModal.vue'
import ontologyEditParamsHp from './data/ontologyEditParamsHp.json'
import ontologyTermResponseHp from './data/ontologyTermResponseHp.json'
import ontologyEditParamsMulti from './data/ontologyEditParamsMulti.json'
import ontologyEditParamsAny from './data/ontologyEditParamsAny.json'
import ontologyTermInitialHp from './data/ontologyTermInitialHp.json'
import ontologyTermInitialMulti from './data/ontologyTermInitialMulti.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Set up fetch-mock-jest
const fetchMock = require('fetch-mock-jest')

// Init data
let propsData
const queryUrlPrefix = '/ontology/ajax/obo/term/query?s='
const queryString = 'term'
const initAjaxUrlHp = '/ontology/ajax/obo/term/list?t=Microcephaly&t=Retrognathia&t=Hypotonia'
const initAjaxUrlMulti = '/ontology/ajax/obo/term/list?t=Homo%20sapiens'

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
    fetchMock.reset()
  })

  it('renders modal with ontology term data', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    // General
    expect(wrapper.find('#sodar-ss-ontology-edit-modal').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(wrapper.vm.getTitle())

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-term').attributes().disabled).toBe(undefined)

    // Alerts
    expect(wrapper.find('.sodar-ss-ontology-alert').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    expect(wrapper.findAll('.sodar-ss-ontology-input-row').length).toBe(3)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)
    const termInputs = wrapper.find('#sodar-ss-ontology-free-row').findAll(
      '.sodar-ss-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal when editing existing term', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()
    await wrapper.findAll(
      '.sodar-ss-ontology-term-item').at(0).find(
      '.sodar-ss-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-term').attributes().disabled).toBe('disabled')

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      expect(termItems.at(i).find('.sodar-ss-btn-up').attributes().disabled).toBe('disabled')
      expect(termItems.at(i).find('.sodar-ss-btn-down').attributes().disabled).toBe('disabled')
      if (i === 0) {
        expect(termItems.at(i).find('.sodar-ss-btn-edit').exists()).toBe(false)
        expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(true)
        expect(termItems.at(i).find('.sodar-ss-btn-stop').attributes().disabled).toBe(undefined)
        expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
      } else {
        expect(termItems.at(i).find('.sodar-ss-btn-edit').exists()).toBe(true)
        expect(termItems.at(i).find('.sodar-ss-btn-edit').attributes().disabled).toBe('disabled')
        expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(false)
        expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe('disabled')
      }
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-ontology-free-row').findAll(
      '.sodar-ss-ontology-input-row')
    expect(termInputs.length).toBe(3)
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe('disabled')
    }
    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal after exiting term edit with unchanged values', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-ontology-term-item').at(0).find(
      '.sodar-ss-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.find('.sodar-ss-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-term').attributes().disabled).toBe(undefined)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-ontology-free-row').findAll(
      '.sodar-ss-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal after exiting term edit with modified values', async () => {
    const updateVal = 'Updated'
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-ontology-term-item').at(0).find(
      '.sodar-ss-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-ontology-input-row').at(0).setValue(updateVal)
    await wrapper.find('.sodar-ss-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Changed value
    expect(wrapper.findAll(
      '.sodar-ss-ontology-term-item').at(0).findAll(
      'td').at(0).text()).toBe(updateVal)

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-term').attributes().disabled).toBe(undefined)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    const termInputs = wrapper.find('#sodar-ss-ontology-free-row').findAll(
      '.sodar-ss-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons (update should be allowed now)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('trims input on term edit', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const updateName = 'Updated'
    const updateAcc = 'https://some.accession/001234'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll(
      '.sodar-ss-ontology-term-item').at(0).find(
      '.sodar-ss-btn-edit').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-ontology-input-row').at(0).setValue(
      updateName + '\t')
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(2).setValue(
      updateAcc + '\t')
    await wrapper.find('.sodar-ss-btn-stop').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    // Changed values
    expect(wrapper.vm.value[0].name).toBe(updateName)
    expect(wrapper.vm.value[0].accession).toBe(updateAcc)
  })

  it('reorders terms on down arrow click', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const firstTermName = ontologyEditParamsHp.value[0].name
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(firstTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')

    await termItems.at(0).find('.sodar-ss-btn-down').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(firstTermName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('reorders terms on up arrow click', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const firstTermName = ontologyEditParamsHp.value[0].name
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(firstTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')

    await termItems.at(1).find('.sodar-ss-btn-up').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(termItems.at(1).findAll('td').at(0).text()).toBe(firstTermName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('removes term on delete click', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    await termItems.at(0).find('.sodar-ss-btn-delete').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(2)
    expect(termItems.at(0).findAll('td').at(0).text()).toBe(secondTermName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('inserts new term from free entry', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newName = 'New name'
    const ontologyName = 'HP'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)

    await wrapper.findAll('.sodar-ss-ontology-input-row').at(0).setValue(
      newName)
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(1).setValue(
      ontologyName)
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(2).setValue(
      'http://purl.obolibrary.org/obo/HP_9999999')
    await wrapper.find('#sodar-ss-btn-insert').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(4)
    expect(termItems.at(3).findAll('td').at(0).text()).toBe(newName)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('trims new term input in free entry', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newName = 'New name'
    const ontologyName = 'HP'
    const accession = 'http://purl.obolibrary.org/obo/HP_9999999'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.value.length).toBe(3)

    await wrapper.findAll('.sodar-ss-ontology-input-row').at(0).setValue(
      newName + '\t')
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(1).setValue(
      ontologyName)
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(2).setValue(
      accession + '\t')
    await wrapper.find('#sodar-ss-btn-insert').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.vm.value.length).toBe(4)
    expect(wrapper.vm.value[3].name).toBe(newName)
    expect(wrapper.vm.value[3].accession).toBe(accession)
  })

  it('prevents new term insert with incorrect ontology name', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newName = 'New name'
    const ontologyName = 'NCBITAXON'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.findAll('.sodar-ss-ontology-input-row').at(0).setValue(newName)
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(1).setValue(ontologyName)
    await wrapper.findAll('.sodar-ss-ontology-input-row').at(2).setValue('http://purl.obolibrary.org/obo/HP_9999999')
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')
  })

  it('renders term search options', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    expect(termOptions.length).toBe(4)

    for (let i = 0; i < ontologyTermResponseHp.terms.length; i++) {
      const term = ontologyTermResponseHp.terms[i]
      const text = '[' + term.term_id + '] ' + term.name
      expect(termOptions.at(i).text()).toBe(text)
    }
  })

  it('renders search option for an obsolete term', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const terms = [{
      ontology_name: 'HP',
      term_id: 'HP:0002880',
      name: 'obsolete Respiratory difficulties',
      is_obsolete: true,
      replaced_by: 'HP:0002098',
      accession: 'http://purl.obolibrary.org/obo/HP_0002880'
    }]
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({ termOptions: terms })
    await waitNT(wrapper.vm)
    await waitRAF()

    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    expect(termOptions.length).toBe(1)
    expect(termOptions.at(0).text()).toContain('<OBSOLETE>')
  })

  it('inserts new term from option selection', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(4)
    expect(termItems.at(3).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('handles option selection of existing term', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const existingOption = {
      name: 'Microcephaly',
      accession: 'http://purl.obolibrary.org/obo/HP_0000252',
      ontology_name: 'HP'
    }
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(copy(ontologyEditParamsHp), jest.fn())
    wrapper.setData({
      termOptions: [existingOption]
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3) // Nothing should be added
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with term with disallowed list value', async () => {
    const initTerms = copy(ontologyTermInitialHp)
    initTerms.terms = [initTerms.terms[0]]
    const initUrl = '/ontology/ajax/obo/term/list?t=Microcephaly'
    fetchMock.mock(initUrl, initTerms)
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    // Alerts
    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(1)
    const termItem = wrapper.find('.sodar-ss-ontology-term-item')
    expect(termItem.find('.sodar-ss-btn-up').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-btn-down').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-btn-edit').exists()).toBe(true)
    expect(termItem.find('.sodar-ss-btn-edit').attributes().disabled).toBe(undefined)
    expect(termItem.find('.sodar-ss-btn-stop').exists()).toBe(false)
    expect(termItem.find('.sodar-ss-btn-delete').exists()).toBe(true)
    expect(termItem.find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(false)

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with empty value with disallowed list value', async () => {
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = []
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)
  })

  it('replaces existing term with disallowed list value', async () => {
    const initTerms = copy(ontologyTermInitialHp)
    initTerms.terms = [initTerms.terms[0]]
    const initUrl = '/ontology/ajax/obo/term/list?t=Microcephaly'
    fetchMock.mock(initUrl, initTerms)
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(1)
    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(termItems.at(0).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('inserts term with disallowed list value', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = []
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    wrapper.setData({
      termOptions: ontologyTermResponseHp.terms
    })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(0)
    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)

    const termOptions = wrapper.find('#sodar-ss-ontology-select-term').findAll('option')
    await termOptions.at(0).trigger('dblclick')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(termItems.at(0).find('td').text()).toBe(ontologyTermResponseHp.terms[0].name)
    // Initial value was false, so this should not be displayed
    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-ontology-term-item').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('renders modal after deleting term with disallowed list value', async () => {
    const initTerms = copy(ontologyTermInitialHp)
    initTerms.terms = [initTerms.terms[0]]
    const initUrl = '/ontology/ajax/obo/term/list?t=Microcephaly'
    fetchMock.mock(initUrl, initTerms)
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    modalParams.value = [modalParams.value[0]]
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(1)
    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(true)
    expect(wrapper.find('.sodar-ss-ontology-term-item').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(false)

    await wrapper.find('.sodar-ss-btn-delete').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(0)
    expect(wrapper.find('#sodar-ss-ontology-no-list').exists()).toBe(false)
    expect(wrapper.find('.sodar-ss-ontology-term-item').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe(undefined)
  })

  it('renders modal with no imported ontologies', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.sodarOntologies = {}
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-select-limit').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-order-check').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-select-term').exists()).toBe(false)

    // Alerts
    expect(wrapper.find('#sodar-ss-ontology-no-imports').exists()).toBe(true)

    // Terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)
  })

  it('renders modal with ontology term data', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsHp, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    // General
    expect(wrapper.find('#sodar-ss-ontology-edit-modal').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(wrapper.vm.getTitle())

    // Term search
    expect(wrapper.find('#sodar-ss-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-order-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-ontology-select-term').attributes().disabled).toBe(undefined)

    // Alerts
    expect(wrapper.find('.sodar-ss-ontology-alert').exists()).toBe(false)
    expect(wrapper.find('#sodar-ss-ontology-no-imports').exists()).toBe(false)

    // Existing terms
    const termItems = wrapper.findAll('.sodar-ss-ontology-term-item')
    expect(termItems.length).toBe(3)
    for (let i = 0; i < termItems.length; i++) {
      let upDisabled
      let downDisabled
      if (i === 0) upDisabled = 'disabled'
      if (i === termItems.length - 1) downDisabled = 'disabled'
      expect(termItems.at(i).find('.sodar-ss-btn-up').attributes().disabled).toBe(upDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-down').attributes().disabled).toBe(downDisabled)
      expect(termItems.at(i).find('.sodar-ss-btn-edit').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-delete').attributes().disabled).toBe(undefined)
      expect(termItems.at(i).find('.sodar-ss-btn-stop').exists()).toBe(false)
    }

    // Term insert row
    expect(wrapper.findAll('.sodar-ss-ontology-input-row').length).toBe(3)
    expect(wrapper.find('#sodar-ss-ontology-free-row').exists()).toBe(true)
    const termInputs = wrapper.find('#sodar-ss-ontology-free-row').findAll(
      '.sodar-ss-ontology-input-row')
    for (let i = 0; i < termInputs.length; i++) {
      expect(termInputs.at(i).attributes().disabled).toBe(undefined)
    }
    expect(wrapper.find('#sodar-ss-btn-insert').attributes().disabled).toBe('disabled')

    // Bottom buttons
    expect(wrapper.find('#sodar-ss-btn-update').attributes().disabled).toBe('disabled')
  })

  it('renders modal with multiple allowed ontologies', async () => {
    fetchMock.mock(initAjaxUrlMulti, ontologyTermInitialMulti)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    // Term search
    const selectLimit = wrapper.find('#sodar-ss-ontology-select-limit')
    expect(selectLimit.attributes().disabled).toBe(undefined)
    expect(selectLimit.findAll('option').length).toBe(3) // Includes null
    expect(wrapper.find('#sodar-ss-ontology-select-limit').attributes().disabled).toBe(undefined)
  })

  it('builds query url with a single allowed ontology', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const url = queryUrlPrefix + queryString + '&o=HP'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsHp, jest.fn())
    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with a multiple allowed ontologies', async () => {
    fetchMock.mock(initAjaxUrlMulti, ontologyTermInitialMulti)
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON&o=CL'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with no ontology limit', async () => {
    fetchMock.mock(initAjaxUrlMulti, ontologyTermInitialMulti)
    const url = queryUrlPrefix + queryString
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsAny, jest.fn())
    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url limited to selected ontology', async () => {
    fetchMock.mock(initAjaxUrlMulti, ontologyTermInitialMulti)
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    // TODO: How to trigger click on v-select with size=1?
    wrapper.setData({ queryOntologyLimit: 'NCBITAXON' })
    await waitNT(wrapper.vm)
    await waitRAF()
    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('builds query url with ontology-based ordering', async () => {
    fetchMock.mock(initAjaxUrlMulti, ontologyTermInitialMulti)
    const url = queryUrlPrefix + queryString + '&o=NCBITAXON&o=CL&order=1'
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(ontologyEditParamsMulti, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()
    wrapper.setData({ queryOntologyOrder: true })
    expect(wrapper.vm.getQueryUrl(queryString)).toBe(url)
  })

  it('handles term paste', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newValue = [
      {
        name: 'Aggressive behavior',
        ontology_name: 'HP',
        accession: 'http://purl.obolibrary.org/obo/HP_0000718'
      },
      {
        name: 'Short neck',
        ontology_name: 'HP',
        accession: 'http://purl.obolibrary.org/obo/HP_0000470'
      }
    ]
    const modalParams = copy(ontologyEditParamsHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onPasteInput(JSON.stringify(newValue))
    for (let i = 0; i < newValue.length; i++) {
      expect(wrapper.vm.value[i].name).toBe(newValue[i].name)
      expect(wrapper.vm.value[i].ontology_name).toBe(newValue[i].ontology_name)
      expect(wrapper.vm.value[i].accession).toBe(newValue[i].accession)
    }
  })

  it('handles term paste with disallowed list (should fail)', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newValue = [
      {
        name: 'Aggressive behavior',
        ontology_name: 'HP',
        accession: 'http://purl.obolibrary.org/obo/HP_0000718'
      },
      {
        name: 'Short neck',
        ontology_name: 'HP',
        accession: 'http://purl.obolibrary.org/obo/HP_0000470'
      }
    ]
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.allow_list = false
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onPasteInput(JSON.stringify(newValue))
    for (let i = 0; i < wrapper.vm.value.length; i++) {
      expect(wrapper.vm.value[i].name).toBe(modalParams.value[i].name)
      expect(wrapper.vm.value[i].ontology_name).toBe(modalParams.value[i].ontology_name)
      expect(wrapper.vm.value[i].accession).toBe(modalParams.value[i].accession)
    }
  })

  it('handles term paste with disallowed ontologies (should fail)', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    const newValue = [
      {
        name: 'Aggressive behavior',
        ontology_name: 'ORDO',
        accession: 'http://purl.obolibrary.org/obo/HP_0000718'
      },
      {
        name: 'Short neck',
        ontology_name: 'NCBITAXON',
        accession: 'http://purl.obolibrary.org/obo/HP_0000470'
      }
    ]
    const modalParams = copy(ontologyEditParamsHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onPasteInput(JSON.stringify(newValue))
    for (let i = 0; i < wrapper.vm.value.length; i++) {
      expect(wrapper.vm.value[i].name).toBe(modalParams.value[i].name)
      expect(wrapper.vm.value[i].ontology_name).toBe(modalParams.value[i].ontology_name)
      expect(wrapper.vm.value[i].accession).toBe(modalParams.value[i].accession)
    }
  })

  it('handles term paste with no ontology limit', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    const newValue = [
      {
        name: 'Aggressive behavior',
        ontology_name: 'ORDO',
        accession: 'http://purl.obolibrary.org/obo/HP_0000718'
      },
      {
        name: 'Short neck',
        ontology_name: 'NCBITAXON',
        accession: 'http://purl.obolibrary.org/obo/HP_0000470'
      }
    ]
    const modalParams = copy(ontologyEditParamsHp)
    modalParams.editConfig.ontologies = []
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onPasteInput(JSON.stringify(newValue))
    for (let i = 0; i < newValue.length; i++) {
      expect(wrapper.vm.value[i].name).toBe(newValue[i].name)
      expect(wrapper.vm.value[i].ontology_name).toBe(newValue[i].ontology_name)
      expect(wrapper.vm.value[i].accession).toBe(newValue[i].accession)
    }
  })

  it('handles term paste with invalid JSON (should fail)', async () => {
    fetchMock.mock(initAjaxUrlHp, ontologyTermInitialHp)
    jest.spyOn(console, 'error').mockImplementation(jest.fn())
    const newValue = 'qwertyuiop;"asdfghjk'
    const modalParams = copy(ontologyEditParamsHp)
    const wrapper = mount(OntologyEditModal, {
      localVue, propsData: propsData
    })
    wrapper.vm.showModal(modalParams, jest.fn())
    await waitNT(wrapper.vm)
    await waitRAF()

    await wrapper.vm.onPasteInput(newValue)
    for (let i = 0; i < wrapper.vm.value.length; i++) {
      expect(wrapper.vm.value[i].name).toBe(modalParams.value[i].name)
      expect(wrapper.vm.value[i].ontology_name).toBe(modalParams.value[i].ontology_name)
      expect(wrapper.vm.value[i].accession).toBe(modalParams.value[i].accession)
    }
  })

  // TODO: Test values returned to finishEditCb
  // TODO: For some reason expected values return "editable" even after delete?
  // TODO: (Some async testing issue?)
})
