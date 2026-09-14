import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MultiPresetCustomField from './MultiPresetCustomField.vue'

const presets = ['German', 'English', 'Japanese']

function view(values: string[] = []) {
  return mount(MultiPresetCustomField, {
    props: { id: 'languages', label: 'Languages', modelValue: values, presets },
  })
}

describe('MultiPresetCustomField', () => {
  it('starts with an empty array and adds multiple presets in selection order', async () => {
    const wrapper = view()
    const choices = wrapper.findAll('input[type="checkbox"]')
    await choices[0].setValue(true)
    await wrapper.setProps({ modelValue: ['German'] })
    await choices[1].setValue(true)
    expect(wrapper.emitted('update:modelValue')).toEqual([[['German']], [['German', 'English']]])
  })

  it('adds, keeps, and removes unknown custom values without CSV or sentinels', async () => {
    const wrapper = view(['German', 'Latin'])
    expect(wrapper.text()).toContain('Latin')
    await wrapper.get('#languages-custom').setValue('Klingon')
    await wrapper.findAll('button').find((button) => button.text() === 'Add')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['German', 'Latin', 'Klingon']])
    await wrapper.get('[aria-label="Remove Latin"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['German']])
  })

  it('removes presets, rejects trimmed duplicates, and follows external updates', async () => {
    const wrapper = view(['German', 'English'])
    await wrapper.get('[aria-label="Remove German"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['English']])
    await wrapper.setProps({ modelValue: ['German'] })
    await wrapper.get('#languages-custom').setValue(' German ')
    await wrapper.findAll('button').find((button) => button.text() === 'Add')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['English']])
    await wrapper.setProps({ modelValue: ['Japanese', 'Latin'] })
    expect(wrapper.text()).toContain('Japanese')
    expect(wrapper.text()).toContain('Latin')
  })
})
