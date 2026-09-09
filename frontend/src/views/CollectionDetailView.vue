<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { ApiError } from '@/api/client'
import type { CollectionMember, CollectionUpdatePayload, MemberPayload } from '@/api/collections'
import { useCollectionsStore } from '@/stores/collections'

const route = useRoute()
const router = useRouter()
const collections = useCollectionsStore()
const editing = ref(false)
const saving = ref(false)
const saveError = ref(false)
const confirmingDelete = ref(false)
const deleting = ref(false)
const deleteError = ref(false)
const name = ref('')
const description = ref('')
const type = ref('movies')
const memberUsername = ref('')
const memberRole = ref<CollectionMember['role']>('viewer')
const memberError = ref('')
const memberBusy = ref(false)
const removingMemberId = ref<number | null>(null)
const transferUsername = ref('')
const confirmingTransfer = ref(false)
const transferError = ref('')
const transferring = ref(false)

const canEdit = computed(() => ['owner', 'admin'].includes(collections.collection?.role ?? ''))
const canDelete = computed(() => collections.collection?.role === 'owner')
const canManageMembers = computed(() => ['owner', 'admin'].includes(collections.collection?.role ?? ''))
const canTransferOwnership = computed(() => collections.collection?.role === 'owner')

function collectionIdFromRoute(): number {
  return Number(route.params.collectionId)
}

async function loadCollection(): Promise<void> {
  editing.value = false
  confirmingDelete.value = false
  await collections.loadCollection(collectionIdFromRoute())
  if (collections.collection) {
    name.value = collections.collection.name
    description.value = collections.collection.description ?? ''
    type.value = collections.collection.type
    if (canManageMembers.value) await collections.loadMembers(collections.collection.id)
  }
}

function memberDisplayName(member: { display_name: string | null; username: string }): string {
  return member.display_name || member.username
}

function memberActionError(error: unknown, action: 'add' | 'update' | 'remove' | 'transfer'): string {
  if (!(error instanceof ApiError)) return `The member could not be ${action === 'add' ? 'added' : action === 'remove' ? 'removed' : 'updated'}. Please try again.`
  if (error.status === 409) {
    return action === 'transfer'
      ? 'You already own this collection.'
      : 'That user is already a member of this collection.'
  }
  if (error.status === 404) return 'The collection or requested user is unavailable.'
  if (error.status === 403) return 'You no longer have permission for this action.'
  if (error.status === 422) return 'Enter a valid username and role.'
  return 'This action could not be completed. Please try again.'
}

async function addMember(): Promise<void> {
  if (!collections.collection) return
  memberBusy.value = true
  memberError.value = ''
  const payload: MemberPayload = { username: memberUsername.value.trim(), role: memberRole.value }
  try {
    await collections.addCollectionMember(collections.collection.id, payload)
    memberUsername.value = ''
    memberRole.value = 'viewer'
  } catch (error) {
    memberError.value = memberActionError(error, 'add')
  } finally {
    memberBusy.value = false
  }
}

async function updateMemberRole(member: CollectionMember, event: Event): Promise<void> {
  if (!collections.collection) return
  memberError.value = ''
  const role = (event.target as HTMLSelectElement).value as CollectionMember['role']
  try {
    await collections.updateCollectionMember(collections.collection.id, member, role)
  } catch (error) {
    memberError.value = memberActionError(error, 'update')
  }
}

async function removeMember(): Promise<void> {
  if (!collections.collection || removingMemberId.value === null) return
  memberBusy.value = true
  memberError.value = ''
  try {
    await collections.deleteCollectionMember(collections.collection.id, removingMemberId.value)
    removingMemberId.value = null
  } catch (error) {
    memberError.value = memberActionError(error, 'remove')
  } finally {
    memberBusy.value = false
  }
}

function startTransferConfirmation(): void {
  transferError.value = ''
  confirmingTransfer.value = true
}

async function transferOwnership(): Promise<void> {
  transferError.value = ''
  transferring.value = true
  try {
    await collections.transferCurrentOwnership(transferUsername.value.trim())
    transferUsername.value = ''
    confirmingTransfer.value = false
  } catch (error) {
    transferError.value = memberActionError(error, 'transfer')
  } finally {
    transferring.value = false
  }
}

watch(() => route.params.collectionId, loadCollection, { immediate: true })

function beginEditing(): void {
  if (!collections.collection) return
  name.value = collections.collection.name
  description.value = collections.collection.description ?? ''
  type.value = collections.collection.type
  saveError.value = false
  editing.value = true
}

async function saveCollection(): Promise<void> {
  saving.value = true
  saveError.value = false
  const payload: CollectionUpdatePayload = {
    name: name.value.trim(),
    type: type.value,
    description: description.value.trim() || null,
  }
  try {
    await collections.updateCurrentCollection(payload)
    editing.value = false
  } catch {
    saveError.value = true
  } finally {
    saving.value = false
  }
}

async function removeCollection(): Promise<void> {
  deleting.value = true
  deleteError.value = false
  try {
    await collections.deleteCurrentCollection()
    await router.push({ name: 'collections' })
  } catch {
    deleteError.value = true
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <section class="page-content" aria-labelledby="collection-heading">
    <RouterLink class="back-link" :to="{ name: 'collections' }">← All collections</RouterLink>
    <p v-if="collections.detailLoading" class="state-message" role="status">Loading collection…</p>
    <div v-else-if="collections.detailError" class="empty-state state-error" role="alert">
      <h1>Collection unavailable</h1>
      <p v-if="collections.detailError.status === 403">You do not have permission to open this collection.</p>
      <p v-else-if="collections.detailError.status === 404">This collection is no longer available to you.</p>
      <p v-else>We could not load this collection. Please try again.</p>
    </div>
    <template v-else-if="collections.collection">
      <div class="page-heading detail-heading">
        <div>
          <p class="eyebrow">Collection <span class="role-pill">{{ collections.collection.role }}</span></p>
          <h1 id="collection-heading">{{ collections.collection.name }}</h1>
          <p>{{ collections.collection.description || 'No description yet.' }}</p>
          <p class="owner-label">Owner: {{ memberDisplayName(collections.collection.owner) }} <span>({{ collections.collection.owner.username }})</span></p>
        </div>
        <div class="action-row">
          <RouterLink class="button-secondary button-link" :to="{ name: 'locations', params: { collectionId: collections.collection.id } }">Locations</RouterLink>
          <a class="button-secondary button-link" :href="`/collections/${collections.collection.id}/catalog`">Catalog</a>
          <button v-if="canEdit" type="button" class="button-secondary" @click="beginEditing">Edit details</button>
          <button v-if="canDelete" type="button" class="button-danger" @click="confirmingDelete = true">
            Delete collection
          </button>
        </div>
      </div>

      <dl class="metadata-grid panel">
        <div><dt>Type</dt><dd>{{ collections.collection.type === 'movies' ? 'Movies' : collections.collection.type }}</dd></div>
        <div><dt>Your role</dt><dd>{{ collections.collection.role }}</dd></div>
      </dl>

      <section v-if="canManageMembers" class="members-panel panel" aria-labelledby="members-heading">
        <div class="section-heading">
          <div><p class="eyebrow">Sharing</p><h2 id="members-heading">Members</h2></div>
        </div>
        <p v-if="collections.membersError" class="form-error" role="alert">Members could not be loaded. Please try again.</p>
        <p v-else-if="collections.members.length === 0" class="member-empty">No members have been added yet.</p>
        <ul v-else class="member-list" aria-label="Collection members">
          <li v-for="member in collections.members" :key="member.id" class="member-row">
            <div><strong>{{ memberDisplayName(member) }}</strong> <span>({{ member.username }})</span></div>
            <label class="member-role">Role
              <select :value="member.role" @change="updateMemberRole(member, $event)">
                <option value="admin">Admin</option><option value="editor">Editor</option><option value="viewer">Viewer</option>
              </select>
            </label>
            <button type="button" class="button-danger button-compact" @click="removingMemberId = member.id">Remove</button>
          </li>
        </ul>
        <form class="member-form" @submit.prevent="addMember">
          <h3>Add a member</h3>
          <label>Exact username<input v-model="memberUsername" required autocomplete="off" /></label>
          <label>Role<select v-model="memberRole"><option value="admin">Admin</option><option value="editor">Editor</option><option value="viewer">Viewer</option></select></label>
          <button type="submit" :disabled="memberBusy">{{ memberBusy ? 'Adding…' : 'Add member' }}</button>
        </form>
        <p v-if="memberError" class="form-error" role="alert">{{ memberError }}</p>
        <section v-if="removingMemberId !== null" class="confirmation member-confirmation" aria-labelledby="remove-member-heading">
          <h3 id="remove-member-heading">Remove this member?</h3><p>They will no longer have access to this collection.</p>
          <div class="action-row"><button type="button" class="button-danger" :disabled="memberBusy" @click="removeMember">{{ memberBusy ? 'Removing…' : 'Confirm remove' }}</button><button type="button" class="button-secondary" :disabled="memberBusy" @click="removingMemberId = null">Cancel</button></div>
        </section>
      </section>

      <section v-if="canTransferOwnership" class="transfer-panel panel" aria-labelledby="transfer-heading">
        <p class="eyebrow">Owner action</p><h2 id="transfer-heading">Transfer ownership</h2>
        <p>Transfer to an existing local user by exact username.</p>
        <form v-if="!confirmingTransfer" class="member-form" @submit.prevent="startTransferConfirmation">
          <label>New owner username<input v-model="transferUsername" required autocomplete="off" /></label>
          <button type="submit">Review transfer</button>
        </form>
        <section v-else class="confirmation" aria-labelledby="confirm-transfer-heading">
          <h3 id="confirm-transfer-heading">Transfer ownership to {{ transferUsername }}?</h3>
          <p>This user becomes the new owner. You will remain an admin member; the new owner will not also be a member.</p>
          <div class="action-row"><button type="button" class="button-danger" :disabled="transferring" @click="transferOwnership">{{ transferring ? 'Transferring…' : 'Confirm transfer' }}</button><button type="button" class="button-secondary" :disabled="transferring" @click="confirmingTransfer = false">Cancel</button></div>
        </section>
        <p v-if="transferError" class="form-error" role="alert">{{ transferError }}</p>
      </section>

      <form v-if="editing" class="collection-form panel" @submit.prevent="saveCollection">
        <h2>Edit collection details</h2>
        <label>Name<input v-model="name" required maxlength="255" /></label>
        <label>Collection type<select v-model="type"><option value="movies">Movies</option><option value="board_games">Board games</option></select></label>
        <label>Description <span class="optional">optional</span><textarea v-model="description" rows="3" maxlength="2000" /></label>
        <p v-if="saveError" class="form-error" role="alert">Changes could not be saved. Please try again.</p>
        <div class="action-row"><button type="submit" :disabled="saving">{{ saving ? 'Saving…' : 'Save changes' }}</button><button type="button" class="button-secondary" @click="editing = false">Cancel</button></div>
      </form>

      <section v-if="confirmingDelete" class="confirmation panel" aria-labelledby="delete-heading">
        <h2 id="delete-heading">Delete {{ collections.collection.name }}?</h2>
        <p>This permanently removes the collection and its related data. This cannot be undone.</p>
        <p v-if="deleteError" class="form-error" role="alert">The collection could not be deleted. Please try again.</p>
        <div class="action-row"><button type="button" class="button-danger" :disabled="deleting" @click="removeCollection">{{ deleting ? 'Deleting…' : 'Confirm delete' }}</button><button type="button" class="button-secondary" :disabled="deleting" @click="confirmingDelete = false">Cancel</button></div>
      </section>
    </template>
  </section>
</template>
