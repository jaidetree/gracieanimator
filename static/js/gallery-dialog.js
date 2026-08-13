const container = document.querySelector('.image-gallery__grid')
const dialog = document.getElementById('gallery-dialog')
const totalItems = container.children.length

function getGalleryIndex(href) {
	return Array.from(
		container.querySelectorAll('.image-gallery__link'),
	).findIndex(anchor => anchor.href === href)
}

function getGalleryItemByIndex(index) {
	return container.children.item(index)
}

function wrapIndex(index) {
	if (index < 0) {
		return totalItems - 1
	}
	if (index >= totalItems) {
		return 0
	}

	return index
}

function swapImage({ index, href, title }) {
	const imgs = dialog.querySelectorAll('.gallery-dialog__img')
	const prevItem = getGalleryItemByIndex(wrapIndex(index - 1))
	const nextItem = getGalleryItemByIndex(wrapIndex(index + 1))

	imgs.forEach(el => {
		el.src = href
		el.alt = title
	})

	dialog.querySelector('.gallery-dialog__select--self').value = href

	const prevThumbnailBtn = dialog.querySelector('.gallery-dialog__select--prev')
	const { href: prevHref, title: prevTitle } = prevItem.querySelector('a')

	prevThumbnailBtn.value = prevHref
	prevThumbnailBtn.querySelector('img').src = prevHref
	prevThumbnailBtn.querySelector('img').alt = prevTitle

	const prevArrowBtn = dialog.querySelector('.gallery-dialog__prev')

	prevArrowBtn.value = prevHref

	const nextThumbnailBtn = dialog.querySelector('.gallery-dialog__select--next')
	const { href: nextHref, title: nextTitle } = nextItem.querySelector('a')

	nextThumbnailBtn.value = nextHref
	nextThumbnailBtn.querySelector('img').src = nextHref
	nextThumbnailBtn.querySelector('img').alt = nextTitle

	const nextArrowBtn = dialog.querySelector('.gallery-dialog__next')

	nextArrowBtn.value = prevHref
}

function displayGalleryDialog(el) {
	const anchor = el.querySelector('a')
	const { title, href } = anchor
	const index = getGalleryIndex(href)

	swapImage({ index, href, title })
	dialog.showModal()
}

function handleClickItem(e) {
	const el = e.target.closest('figure')

	if (
		!el ||
		!el.classList.contains('image-gallery__item') ||
		!('showModal' in dialog)
	) {
		return
	}

	e.preventDefault()
	e.stopPropagation()

	displayGalleryDialog(el)
}

function handleClickNavItem(e) {
	const el = e.target.closest('button')

	if (!el) {
		return
	}

	const href = el.value
	const index = getGalleryIndex(href)
	const item = getGalleryItemByIndex(index)

	swapImage({ href, title: item.title, index })
}

container.addEventListener('click', handleClickItem)

dialog
	.querySelector('.gallery-dialog__nav')
	.addEventListener('click', handleClickNavItem)
