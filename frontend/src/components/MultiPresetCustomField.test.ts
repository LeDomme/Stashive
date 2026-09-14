import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import MultiPresetCustomField from './MultiPresetCustomField.vue'

const presets = ['German', 'English', 'Japanese']
function view(values: string[] = []) {
  return mount(MultiPresetCustomField, { props: { id: 'languages', label: 'Languages', modelValue: values, presets } })
}
async function open(wrapper: ReturnType<typeof view>) { await wrapper.get('#languages').trigger('click') }

describe('MultiPresetCustomField', () => {
  it('is a closed compact dropdown until opened and summarizes selections', async () => {
    const wrapper = view(['German', 'English', 'Latin'])
    expect(wrapper.get('#languages').text()).toContain('German, English, +1')
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(false)
    await open(wrapper)
    expect(wrapper.findAll('input[type="checkbox"]')).toHaveLength(3)
    expect(wrapper.text()).toContain('Latin')
  })

  it('adds and deselects multiple presets without duplicates', async () => {
    const wrapper = view()
    await open(wrapper)
    const choices = wrapper.findAll('input[type="checkbox"]')
    await choices[0].setValue(true)
    await wrapper.setProps({ modelValue: ['German'] })
    await choices[1].setValue(true)
    await wrapper.setProps({ modelValue: ['German', 'English'] })
    await choices[0].setValue(false)
    expect(wrapper.emitted('update:modelValue')).toEqual([[['German']], [['German', 'English']], [['English']]])
  })

  it('adds, preserves and removes custom or externally updated unknown values', async () => {
    const wrapper = view(['German', 'Latin'])
    await open(wrapper)
    await wrapper.get('#languages-custom').setValue('Klingon')
    await wrapper.findAll('button').find((button) => button.text() === 'Add')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['German', 'Latin', 'Klingon']])
    await wrapper.get('[aria-label="Remove Latin"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['German']])
    await wrapper.setProps({ modelValue: ['Japanese', 'Old Norse'] })
    expect(wrapper.text()).toContain('Old Norse')
  })

  it('rejects trimmed duplicates and closes with Escape or an outside click', async () => {
    const wrapper = view(['German'])
    await open(wrapper)
    await wrapper.get('#languages-custom').setValue(' German ')
    await wrapper.findAll('button').find((button) => button.text() === 'Add')!.trigger('click')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('#languages-popover').exists()).toBe(false)
    await open(wrapper)
    document.body.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await wrapper.vm.$nextTick()
    expect(wrapper.find('#languages-popover').exists()).toBe(false)
  })
})
