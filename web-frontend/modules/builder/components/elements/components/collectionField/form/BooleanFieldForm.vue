<template>
  <form @submit.prevent @keydown.enter.prevent>
    <FormGroup
      small-label
      :label="$t('textFieldForm.fieldValueLabel')"
      required
      horizontal
      class="margin-bottom-2"
    >
      <InjectedFormulaInput
        v-model="values.value"
        :placeholder="$t('textFieldForm.fieldValuePlaceholder')"
      />
      <template #after-input>
        <CustomStyle
          v-model="values.styles"
          style-key="cell"
          :config-block-types="['table']"
          :theme="baseTheme"
          :extra-args="{ onlyCell: true, noAlignment: true }"
          variant="normal"
        />
      </template>
    </FormGroup>
  </form>
</template>

<script>
import collectionFieldForm from '@baserow/modules/builder/mixins/collectionFieldForm'
import InjectedFormulaInput from '@baserow/modules/core/components/formula/InjectedFormulaInput'
import CustomStyle from '@baserow/modules/builder/components/elements/components/forms/style/CustomStyle'

export default {
  name: 'BooleanFieldForm',
  components: { InjectedFormulaInput, CustomStyle },
  mixins: [collectionFieldForm],
  data() {
    return {
      allowedValues: ['value', 'styles'],
      values: {
        value: '',
        styles: {},
      },
    }
  },
}
</script>
