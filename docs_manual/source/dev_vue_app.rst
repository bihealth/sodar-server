.. _dev_vue_app:

Samplesheets Vue App Development
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This document provides guidelines for developing the samplesheets Vue3 app for
browsing and editing samplesheets. The app can be found under
``samplesheets/vue3app``. It runs on `Node.js <https://nodejs.org/>`_ and is
served on the Django site using Vite.

.. note::

    This document is under construction. Suggestions for improvements are
    welcome.


Development Environment
=======================

The following tools are used to develop the vue3app:

- The app is built on `Vue3 <https://vuejs.org/guide/introduction.html>`_.
- Components are built using the
  `composition API <https://vuejs.org/guide/introduction.html#composition-api>`_.
- Components are written in `TypeScript <https://www.typescriptlang.org/>`_.
- Data storage is done with `Pinia <https://pinia.vuejs.org/>`_.
- Navigation is built on `vue-router <https://router.vuejs.org/>`_ in the hash
  history mode.
- For styling we use
  `boostrap-vue-next <https://bootstrap-vue-next.github.io/bootstrap-vue-next/>`_.
- Sample sheet tables are built with the community version of
  `ag-grid <https://www.ag-grid.com/vue-data-grid/getting-started/>`_.
- Unit testing is handled with `vitest <https://vitest.dev/>`_ and
  `Vue Test Utils <https://test-utils.vuejs.org/guide/>`_.


Development Commands
====================

Run the server with:

.. code-block:: console

    $ make samplesheets_vue

Run tests with:

.. code-block:: console

    $ make test_samplesheets_vue

Restrict tests to a specific component with:

.. code-block:: console

    $ make test_samplesheets_vue arg=ComponentName


Application Structure
=====================

This section describes the vue3app directory structure along with important
files.

Directory Structure
-------------------

The directory structure for ``samplesheets/vue3app`` is as follows:

::

    vue3app
    ├── src
    │   ├── assets              App assets (currently CSS)
    │   ├── components          General app components
    │   │   ├── editors         Ag-grid editor components
    │   │   ├── modals          Modal components
    │   │   │  └── include      Subcomponents to include in modals
    │   │   └── renderers       Ag-grid renderer components
    │   ├── router              Vue-router navigation for the app
    │   ├── stores              Pinia stores
    │   ├── utils               General utilities
    │   └── views               App view components
    └── tests
        ├── data                Data for unit tests
        └── unit                Unit tests

Important Files
---------------

The following files are of special note.

``App.vue``
    App entry point.
``constants.ts``
    General constants for reusable strings etc. are collected here as exports.
``main.ts``
    App setup.
``types.ts``
    TypeScript interfaces are maintained here, except for test-specific
    interfaces or possible single-use internal types.
``stores/appStore.ts``
    General application store, always populated on app startup. Contains the
    general SODAR context retrieved from the server along with variables for
    app operation.
``stores/editStore.ts``
    Editor specific data store, used in edit mode.
``stores/tableStore.ts``
    Data for building the ag-grid tables goes here.
``utils/appUtils.ts``
    General application utilities.
``utils/editUtils.ts``
    Editing-specific utilities.
``utils/gridUtils.ts``
    Utilities specific to building ag-grid tables from data retrieved from the
    server.
``utils/notifyCb.ts``
    API for toast notifications. In most cases this should be accessed through
    ``appStore.notifyCb``.
``views/OverviewView.vue``
    View for displaying the investigation overview.
``views/ParserWarningView.vue``
    View for displaying parser warnings.
``views/StudyView.vue``
    The main view in the application. Displays study and assay tables either for
    browsing or for editing.
``tests/testConstants.ts``
    Testing-specific constants.
``test/testTypes.ts``
    Testing-specific interfaces.
``test/testUtils.ts``
    Testing utilities.


Component Development
=====================

This section provides guidelines and resources for component development.

Component Guidelines
--------------------

- Component functionality should be encapsulated as much as possible.
    * Only use ``defineExpose()`` when necessary, e.g. modal opening methods.
- That said, do not be afraid of placing commonly reusable utilities in an
  utility module.
    * These can be tested, unlike internal component functions.
    * The general wisdom of "avoid utility modules" does not really work for the
      Vue3 composition API.
- Use a common structure for your components whereever possible, based on the
  templates provided further along this document.
    * The Vue3 composition API provides a very non-limited structure for the
      developer which can easily lead into chaos.
- Maintain consistent import order.
    * Vue library
    * vue-router
    * bootstrap-vue-next
    * Other external packages (e.g. ag-grid)
    * Samplesheets vue3app components
    * Stores
    * Utils
    * Types
    * Constants

Component Template
------------------

The following is a basic template for a component with provided divider comments
to help compartmentalize setup content. Imports go on the top of the ``setup``
script without any commented section. Remove comments when not used.

.. code-block:: Vue

    <script setup lang="ts">
    // Constants -------------------------------------------------------------------
    // Interfaces ------------------------------------------------------------------
    // External Data ---------------------------------------------------------------
    // Refs ------------------------------------------------------------------------
    // Internal Vars ---------------------------------------------------------------
    // Computed Vars ---------------------------------------------------------------
    // Setup -----------------------------------------------------------------------
    // Helpers ---------------------------------------------------------------------
    // API and Life Cycle ----------------------------------------------------------
    </script>

    <template>
      <div>
      </div>
    </template>

    <style scoped>
    </style>

Explanations for some of the sections:

Setup
    Code run directly in the component ``setup``.
Helpers
    Internal helpers such as event handlers
API and Life Cycle
    Vue lifecycle hooks, watchers, exposed methods (e.g. modal showing) etc.


Coding Conventions
==================

Miscellaneous vue3app-specific coding conventions are described here.

- Name event handlers as ``onActionName()``, e.g. ``onTitleInput()``.
- Other helper functions should start with a verb
- Reducing line bloat by not breaking lines for every single curly brace is
  totally fine, with reason of course :)
- Don't be shy about adding reused strings as constants in ``constants.ts``.
- Name CSS classes and IDs as ``sodar-ss-*``.


.. _dev_vue_app_test:

Testing
=======

This section presents templates and examples for getting started with unit
testing for the vu3app components.

Unit tests should be placed under ``tests/unit/`` as ``ComponentName.spec.ts``.
As the file name suffix implies, tests are also to be written in TypeScript.

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

    import { useAppStore } from '@/stores/appStore.ts'
    import { useTableStore } from '@/stores/tableStore.ts'
    import { type SodarContext } from '@/components.ts'

    import { sodarContext } from '../data/sodarContext.ts'
    import { copy } from '../testUtils.ts'

    beforeEach(() => {
      setActivePinia(createPinia())
      const appStore = useAppStore()
      const tableStore = useTableStore()
      appStore.sodarContext = copy(sodarContext) as SodarContext
    })

Vue-Bootstrap-Next Setup Example
--------------------------------

For components which make use of vue-bootstrap-next components, we need to set
up the relevant plugin:

.. code-block:: typescript

    import { config } from '@vue/test-utils'
    import { createBootstrap } from 'bootstrap-vue-next/plugins/createBootstrap'
    config.global.plugins = [createBootstrap()]


TODO
====

- Add more vue3app-specific coding conventions
- Add component templates for e.g. modals and ag-grid renderers/editors
- Describe table retrieval and building
- Describe differences between browsing mode and edit mode
- Describe store variables
- **TBD:** More as needed
