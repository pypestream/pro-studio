<template>
  <form @submit.prevent @keydown.enter.prevent>
    <FormGroup
      small-label
      :label="$t('generalForm.labelTitle')"
      class="margin-bottom-2"
      horizontal
      required
    >
      <InjectedFormulaInput
        v-model="values.label"
        :placeholder="$t('buttonFieldForm.labelPlaceholder')"
      />
      <template #after-input>
        <CustomStyle
          v-model="values.styles"
          style-key="cell"
          :config-block-types="['table', 'button']"
          :theme="baseTheme"
          :extra-args="{ onlyCell: true, noAlignment: true }"
          variant="normal"
        />
      </template>
    </FormGroup>
    <Alert>
      {{ $t('buttonFieldForm.infoMessage') }}
    </Alert>
  </form>
</template>

<script>
import collectionFieldForm from '@baserow/modules/builder/mixins/collectionFieldForm'
import InjectedFormulaInput from '@baserow/modules/core/components/formula/InjectedFormulaInput'
import CustomStyle from '@baserow/modules/builder/components/elements/components/forms/style/CustomStyle'

export default {
  name: 'ButtonFieldForm',
  components: { InjectedFormulaInput, CustomStyle },
  mixins: [collectionFieldForm],
  data() {
    return {
      allowedValues: ['label', 'styles'],
      values: {
        label: '',
        styles: {},
      },
    }
  },
}
</script>
