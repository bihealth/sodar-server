.. _dev_resource:

Development Resources
^^^^^^^^^^^^^^^^^^^^^

This section provides general guidelines and resources on SODAR development.


SODAR Core and SODAR
====================

The SODAR Django server is built on the
`SODAR Core <https://github.com/bihealth/sodar-core>`_ framework. To get started
with developing for SODAR, it is strongly recommend to get acquaintanced with
the framework and its `documentation <https://sodar-core.readthedocs.io/>`_.

Specifically, the
`development section <https://sodar-core.readthedocs.io/en/latest/development.html>`_
of the SODAR Core documentation lists guidelines and resources for development.
Unless explicitly stated otherwise, SODAR Core guidelines also apply to SODAR
development. Reading this section is strongly recommended.

For a breakdown on which applications are imported from SODAR Core and which are
native to SODAR, see :ref:`dev_apps`.


Hard-Coded App Imports
======================

Generally, hard-coded imports between apps, with the exception of
``projectroles``, are discouraged due to the dynamic nature of enabling and
disabling SODAR Core apps. In the case of SODAR, direct imports from the
``samplesheets`` app in the ``landingzones`` app are considered acceptable, as
the latter app would not exist without the former. The same is true for the
study and assay sub-apps within ``samplesheets``.


.. _dev_resource_vue_test:

Vue App Unit Testing
====================

The samplesheets Vue3 app, introduced in v1.3, is expected to be unit tested
with Vitest and Vue Test Utils. Tests should be written in Typescript. This
section presents templates and examples for getting started with unit testing
for the Vue3 app components.

Basic Component Test Template
-----------------------------

This example sets up a barebones unit test file for a Vue3 app component.

.. code-block:: typescript

    import { beforeEach, describe, expect, test } from 'vitest'
    import { mount } from '@vue/test-utils'

    import YourComponent from '@/components/YourComponent.vue'

    describe('YourComponent.vue', () => {
      beforeEach(() => {})

      test('render component', async () => {
        const wrapper = mount(YourComponent)
        // TODO: Test here
      })
    })

Test Template with Properties
-----------------------------

This example sets up a component test with props for the component.

.. code-block:: typescript

    import { beforeEach, describe, expect, test } from 'vitest'
    import { mount, type VueWrapper } from '@vue/test-utils'

    import YourComponent from '@/components/YourComponent.vue'
    import { copy } from '../testUtils.ts'
    import { PROJECT_UUID } from '../testConstants.ts'

    const defaultProps = {}
    let props

    describe('YourComponent.vue', () => {
      function mountComponent (): VueWrapper {
        return mount(YourComponent, { props: props })
      }
      beforeEach(() => {
        props = copy(defaultProps)
      })

      test('render component', async () => {
        const wrapper = mountComponent()
        // TODO: Test here
      })
    })

Modal Test Template
-------------------

This example demonstrates component testing with a bootstrap-vue-next modal.

.. code-block:: typescript

    import { nextTick } from 'vue'
    import { beforeEach, describe, expect, test } from 'vitest'
    import { config, mount, type VueWrapper } from '@vue/test-utils'
    import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'

    import YourComponent from '@/components/modals/YourComponent.vue'

    config.global.plugins = [createBootstrap()]

    describe('YourComponent.vue', () => {
      beforeEach(() => {})

      async function showModal (someAttr: string): Promise<VueWrapper> {
        const wrapper = mount(YourComponent)
        wrapper.vm.show(someAttr)
        await nextTick() // Must wait for all reactive vals to update
        return wrapper
      }

      test('render component', async () => {
        const wrapper = await showModal('someVal')
        // TODO: Test here
      })
    })

Stores Testing Example
----------------------

This example displays how to set up an access Pinia stores in your test cases.

.. code-block:: typescript

    import { setActivePinia, createPinia } from 'pinia'

    import { useAppStore, type SodarContext } from '@/stores/appStore.ts'
    import { useTableStore } from '@/stores/tableStore.ts'

    import { sodarContext } from '../data/sodarContext.ts'
    import { copy } from '../testUtils.ts'

    beforeEach(() => {
      setActivePinia(createPinia())
      const appStore = useAppStore()
      appStore.sodarContext = copy(sodarContext) as SodarContext
      const tableStore = useTableStore()
    })

Vue-Bootstrap-Next Setup Example
--------------------------------

For components which make use of vue-bootstrap-next components, we need to set
up the relevant plugin:

.. code-block:: typescript

    import { config } from '@vue/test-utils'
    import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
    config.global.plugins = [createBootstrap()]
