import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as api from '@/api/catalog'
import * as collectionsApi from '@/api/collections'
import CatalogDetailView from './CatalogDetailView.vue'

vi.mock('@/api/catalog')
vi.mock('@/api/collections')
const router=createRouter({history:createMemoryHistory(),routes:[{path:'/collections/:collectionId/catalog',name:'catalog',component:CatalogDetailView},{path:'/collections/:collectionId/catalog/:entryId',name:'catalog-detail',component:CatalogDetailView}]})
const entry={id:2,collection_id:1,display_title:'Alien',type:'movie',sort_title:'Alien, The',notes:'Classic'}
async function view(role:'owner'|'admin'|'editor'|'viewer'='owner'){
 vi.mocked(collectionsApi.getCollection).mockResolvedValue({id:1,name:'Films',type:'movies',description:null,role,owner:{id:1,username:'owner',display_name:null}})
 vi.mocked(api.getCatalog).mockResolvedValue(entry);vi.mocked(api.listEditions).mockResolvedValue([{id:3,catalog_entry_id:2,display_name:'Blu-ray',release_date:null,publisher:null,region:null,language:null}])
 await router.push('/collections/1/catalog/2');const w=mount(CatalogDetailView,{global:{plugins:[createPinia(),router]}});await flushPromises();return w
}
afterEach(()=>vi.clearAllMocks())
describe('CatalogDetailView',()=>{
 it('renders optional detail fields and editions',async()=>{const w=await view();expect(w.text()).toContain('Alien, The');expect(w.text()).toContain('Classic');expect(w.text()).toContain('Blu-ray')})
 it.each(['owner','admin','editor'] as const)('%s can edit and delete',async role=>{const w=await view(role);expect(w.text()).toContain('Edit entry');expect(w.text()).toContain('Delete entry')})
 it('viewer is read only',async()=>{const w=await view('viewer');expect(w.text()).not.toContain('Edit entry');expect(w.text()).not.toContain('Delete entry')})
 it('sends explicit nulls and requires delete confirmation',async()=>{vi.mocked(api.updateCatalog).mockResolvedValue({...entry,sort_title:null,notes:null});const w=await view();await w.get('button').trigger('click');const inputs=w.findAll('input');await inputs[2].setValue('');await w.get('textarea').setValue('');await w.get('form').trigger('submit');await flushPromises();expect(api.updateCatalog).toHaveBeenCalledWith(1,2,expect.objectContaining({sort_title:null,notes:null}));expect(api.deleteCatalog).not.toHaveBeenCalled();await w.get('.button-danger').trigger('click');expect(w.text()).toContain('physical inventory copies')})
})
