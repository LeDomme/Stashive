import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as collectionsApi from '@/api/collections'
import * as libraryApi from '@/api/library'
import * as locationsApi from '@/api/locations'
import InventoryAddItemView from './InventoryAddItemView.vue'
vi.mock('@/api/collections'); vi.mock('@/api/library'); vi.mock('@/api/locations')
const router=createRouter({history:createMemoryHistory(),routes:[{path:'/collections/:collectionId/inventory/add',name:'inventory-add',component:InventoryAddItemView},{path:'/collections/:collectionId/inventory',name:'inventory',component:InventoryAddItemView},{path:'/collections/:collectionId/inventory/:catalogEntryId',name:'inventory-title',component:InventoryAddItemView}]})
const title={id:2,collection_id:1,display_title:'Alien',type:'movies',sort_title:null,notes:null}; const detail={catalog_entry:title,editions:[{id:3,catalog_entry_id:2,display_name:'Special Edition',media_format:'Blu-ray',release_date:null,publisher:null,region:null,language:null,identifiers:[],copies:[]}]}
async function view(role:'owner'|'editor'|'viewer'='editor'){vi.mocked(collectionsApi.getCollection).mockResolvedValue({...title,name:'Films',role,owner:{id:1,username:'owner',display_name:null}});vi.mocked(locationsApi.listLocationTree).mockResolvedValue([{id:7,collection_id:1,parent_id:null,name:'House',type:'room',description:null,children:[{id:8,collection_id:1,parent_id:7,name:'Shelf',type:'shelf',description:null,children:[]}]}]);vi.mocked(libraryApi.searchTitles).mockResolvedValue([{id:2,catalog_entry_id:2,display_title:'Alien',sort_title:null,type:'movies',edition_count:1,copy_count:0,media_formats:['Blu-ray']}]);vi.mocked(libraryApi.getLibraryTitle).mockResolvedValue(detail);await router.push('/collections/1/inventory/add');const w=mount(InventoryAddItemView,{global:{plugins:[createPinia(),router]}});await flushPromises();return w}
const button = (wrapper: ReturnType<typeof mount>, label: string) => wrapper.findAll('button').find((candidate) => candidate.text() === label)!
async function createTitle(wrapper: ReturnType<typeof mount>, name = 'Arrival') {
  await wrapper.get('input').setValue(name)
  await button(wrapper, `Create new title "${name}"`).trigger('click')
  await flushPromises()
}
async function useExistingTitle(wrapper: ReturnType<typeof mount>) {
  await wrapper.get('input').setValue('Alien')
  await new Promise((resolve) => setTimeout(resolve, 350))
  await flushPromises()
  await button(wrapper, 'Use existing').trigger('click')
  await flushPromises()
}
afterEach(() => vi.clearAllMocks())
describe('InventoryAddItemView',()=>{it('keeps viewers read-only and starts progressively',async()=>{const viewer=await view('viewer');expect(viewer.text()).toContain('do not have permission');expect(viewer.find('form').exists()).toBe(false);const editor=await view();expect(editor.text()).toContain('Title');expect(editor.text()).not.toContain('Physical copy')});it('requires explicit title and edition choices before it submits',async()=>{const w=await view();const input=w.get('input');await input.setValue('Alien');await new Promise(r=>setTimeout(r,350));await flushPromises();expect(libraryApi.searchTitles).toHaveBeenCalledWith(1,'Alien');expect(w.text()).toContain('Use existing');expect(w.text()).toContain('A title with this name already exists');expect(w.text()).not.toContain('Physical copy');await w.get('button').trigger('click');await flushPromises();expect(libraryApi.getLibraryTitle).toHaveBeenCalledWith(1,2);expect(w.text()).toContain('Use this edition');const use=w.findAll('button').find(b=>b.text()==='Use this edition')!;await use.trigger('click');expect(w.text()).toContain('Physical copy')});
  it('submits a new title, new edition and unassigned copy with presets', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 12, edition_id: 13, inventory_item_id: 14 })
    const wrapper = await view()
    await createTitle(wrapper)
    await wrapper.get('#edition').setValue('Steelbook')
    await wrapper.get('#media-format').setValue('Blu-ray')
    await wrapper.get('#condition').setValue('Very Good')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, {
      title: { existing_id: null, new: { display_title: 'Arrival', sort_title: null, notes: null, type: 'movies' } },
      edition: { existing_id: null, new: { display_name: 'Steelbook', media_format: 'Blu-ray', release_date: null, publisher: null, region: null, language: null } },
      copy: { condition: 'Very Good', notes: null, location_id: null },
    })
    expect(libraryApi.listLibrary).toHaveBeenCalledWith(1, {})
    expect(router.currentRoute.value.fullPath).toBe('/collections/1/inventory/12')
  })
  it('submits custom edition, media format and condition for an existing title', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 2, edition_id: 13, inventory_item_id: 14 })
    const wrapper = await view()
    await useExistingTitle(wrapper)
    await button(wrapper, 'Create new edition').trigger('click')
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.get('#media-format').setValue('__custom__'); await wrapper.get('#media-format-custom').setValue('Video CD')
    await wrapper.get('#condition').setValue('__custom__'); await wrapper.get('#condition-custom').setValue('Sealed')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, expect.objectContaining({
      title: { existing_id: 2, new: null },
      edition: expect.objectContaining({ existing_id: null, new: expect.objectContaining({ display_name: '40th Anniversary Edition', media_format: 'Video CD' }) }),
      copy: { condition: 'Sealed', notes: null, location_id: null },
    }))
  })
  it('submits only the selected existing edition and copy details', async () => {
    vi.mocked(libraryApi.addItem).mockResolvedValue({ catalog_entry_id: 2, edition_id: 3, inventory_item_id: 14 })
    const wrapper = await view()
    await useExistingTitle(wrapper)
    await button(wrapper, 'Use this edition').trigger('click')
    await wrapper.get('#condition').setValue('Good')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledWith(1, expect.objectContaining({
      title: { existing_id: 2, new: null }, edition: { existing_id: 3, new: null }, copy: { condition: 'Good', notes: null, location_id: null },
    }))
  })
  it('keeps custom values after an add-item error and allows retrying', async () => {
    vi.mocked(libraryApi.addItem).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ catalog_entry_id: 12, edition_id: 13, inventory_item_id: 14 })
    const wrapper = await view()
    await createTitle(wrapper)
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.get('#media-format').setValue('__custom__'); await wrapper.get('#media-format-custom').setValue('Video CD')
    await wrapper.get('#condition').setValue('__custom__'); await wrapper.get('#condition-custom').setValue('Sealed')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('could not be added')
    expect((wrapper.get('#edition-custom').element as HTMLInputElement).value).toBe('40th Anniversary Edition')
    expect((wrapper.get('#media-format-custom').element as HTMLInputElement).value).toBe('Video CD')
    expect((wrapper.get('#condition-custom').element as HTMLInputElement).value).toBe('Sealed')
    await wrapper.get('form').trigger('submit'); await flushPromises()
    expect(libraryApi.addItem).toHaveBeenCalledTimes(2)
  })
  it('resets dependent edition state when changing the title', async () => {
    const wrapper = await view()
    await createTitle(wrapper)
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await button(wrapper, 'Change').trigger('click')
    expect(wrapper.text()).toContain('Title')
    expect(wrapper.find('#edition').exists()).toBe(false)
    expect(wrapper.findAll('button').some((candidate) => candidate.text() === 'Add item')).toBe(false)
  })
  it('resets new-edition presets when changing the edition choice', async () => {
    const wrapper = await view()
    await createTitle(wrapper)
    await wrapper.get('#edition').setValue('__custom__'); await wrapper.get('#edition-custom').setValue('40th Anniversary Edition')
    await wrapper.findAll('button').filter((candidate) => candidate.text() === 'Change')[1].trigger('click')
    expect(wrapper.find('#edition').exists()).toBe(false)
    expect(wrapper.findAll('button').some((candidate) => candidate.text() === 'Add item')).toBe(false)
  })
})
