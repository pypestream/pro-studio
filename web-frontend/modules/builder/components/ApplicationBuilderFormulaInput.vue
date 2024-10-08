<template>
  <FormulaInputField
    v-bind="$attrs"
    required
    :data-explorer-loading="dataExplorerLoading"
    :data-providers="dataProviders"
    :application-context="
      applicationContext ?? {
        page,
        builder,
        mode,
        ...applicationContextAdditions,
      }
    "
    v-on="$listeners"
  />
</template>

<script>
import FormulaInputField from '@baserow/modules/core/components/formula/FormulaInputField'
import { DataSourceDataProviderType } from '@baserow/modules/builder/dataProviderTypes'

export default {
  name: 'ApplicationBuilderFormulaInput',
  components: { FormulaInputField },
  inject: {
    page: {
      from: 'page',
    },
    builder: {
      from: 'builder',
    },
    mode: {
      from: 'mode',
    },
    applicationContext: {
      from: 'applicationContext',
      default: null,
    },
  },
  props: {
    dataProvidersAllowed: {
      type: Array,
      required: false,
      default: () => [],
    },
    applicationContextAdditions: {
      type: Object,
      required: false,
      default: () => {},
    },
  },
  computed: {
    dataSourceLoading() {
      return this.$store.getters['dataSource/getLoading'](this.page)
    },
    dataSourceContentLoading() {
      return this.$store.getters['dataSourceContent/getLoading'](this.page)
    },
    dataProviders() {
      return this.dataProvidersAllowed.map((dataProviderName) =>
        this.$registry.get('builderDataProvider', dataProviderName)
      )
    },
    /**
     * This mapping defines which data providers are affected by what loading states.
     * Since not all data providers are always used in every data explorer we
     * shouldn't put the data explorer in a loading state whenever some inaccessible
     * data is loading.
     */
    dataProviderLoadingMap() {
      return {
        [DataSourceDataProviderType.getType()]:
          this.dataSourceLoading || this.dataSourceContentLoading,
      }
    },
    dataExplorerLoading() {
      return this.dataProvidersAllowed.some(
        (dataProviderName) => this.dataProviderLoadingMap[dataProviderName]
      )
    },
  },
}
</script>
