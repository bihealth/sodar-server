import { createLocalVue, mount } from '@vue/test-utils'
import { waitNT, waitRAF } from '../utils.js'
import BootstrapVue from 'bootstrap-vue'
import VueClipboard from 'vue-clipboard2'
import OntologyEditModal from '@/components/modals/OntologyEditModal.vue'
import ontologyEditParamsHp from './data/ontologyEditParamsHp.json'

// Set up extended Vue constructor
const localVue = createLocalVue()
localVue.use(BootstrapVue)
localVue.use(VueClipboard)

// Init data
let propsData
const finishEditCb = jest.fn()

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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    // General
    expect(wrapper.find('#sodar-vue-ontology-edit-modal').exists()).toBe(true)
    expect(wrapper.find('h5').text()).toBe(wrapper.vm.getTitle())

    // Term search
    expect(wrapper.find('#sodar-ss-vue-ontology-input-search').attributes().disabled).toBe(undefined)
    expect(wrapper.find('#sodar-ss-vue-ontology-select-limit').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-sort-check').attributes().disabled).toBe('disabled')
    expect(wrapper.find('#sodar-ss-vue-ontology-select-term').attributes().disabled).toBe(undefined)

    // Alert
    expect(wrapper.find('.sodar-ss-vue-ontology-alert').exists()).toBe(false)

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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
    expect(wrapper.find('#sodar-ss-vue-ontology-sort-check').attributes().disabled).toBe('disabled')
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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
    expect(wrapper.find('#sodar-ss-vue-ontology-sort-check').attributes().disabled).toBe('disabled')
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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
    expect(wrapper.find('#sodar-ss-vue-ontology-sort-check').attributes().disabled).toBe('disabled')
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

  it('reorders terms on down arrow click', async () => {
    const firstTermName = ontologyEditParamsHp.value[0].name
    const secondTermName = ontologyEditParamsHp.value[1].name
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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

  it('inserts new term', async () => {
    const newName = 'New name'
    const ontologyName = 'HP'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
    wrapper.setData({ refreshingTerms: false })
    await waitNT(wrapper.vm)
    await waitRAF()

    let termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(3)

    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(0).setValue(newName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(1).setValue(ontologyName)
    await wrapper.findAll('.sodar-ss-vue-ontology-input-row').at(2).setValue('http://purl.obolibrary.org/obo/HP_9999999')
    await wrapper.find('#sodar-ss-vue-btn-insert').trigger('click')
    await waitNT(wrapper.vm)
    await waitRAF()

    termItems = wrapper.findAll('.sodar-ss-vue-ontology-term-item')
    expect(termItems.length).toBe(4)
    expect(termItems.at(3).findAll('td').at(0).text()).toBe(newName)
    expect(wrapper.find('#sodar-ss-vue-btn-update').attributes().disabled).toBe(undefined)
  })

  it('prevents new term insert with incorrect ontology name', async () => {
    const newName = 'New name'
    const ontologyName = 'NCBITAXON'
    const wrapper = mount(OntologyEditModal, {
      localVue,
      propsData: propsData,
      methods: { getInitialTermInfo: jest.fn() }
    })
    wrapper.vm.showModal(ontologyEditParamsHp, finishEditCb)
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
})
