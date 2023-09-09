(defn query-selector
  ([query]
   (js/document.querySelector query))
  ([container query]
   (.querySelector container query)))

(defn query-selector-all
  ([query]
   (query-selector-all js/document query))
  ([container query]
   (-> (.querySelectorAll container query)
       (js/Array.from)
       (js->clj))))

(defn get-by-id
  [id]
  (js/document.getElementById id))


(def pages-container (get-by-id "comic-pages"))
(def comic-viewer (get-by-id "comic-viewer"))

(defn set-page
  [{:keys [img link]}]
  (let [selected (query-selector pages-container ".selected")]
    (set! (.-src comic-viewer)
          (.-src img))
    (set! (.-alt comic-viewer)
          (.-alt img))
    (js/window.history.pushState nil nil (.-href link))
    (doto (.-classList selected)
      (.remove "opacity-100")
      (.remove "selected")
      (.add    "opacity-50"))
    (doto (.-classList link)
      (.remove "opacity-50")
      (.add    "opacity-100")
      (.add    "selected"))))

(defn on-click-page
  [event]
  (let [target (.-target event)
        parent (.-parentNode target)]
    (when (= (.-tagName target) "IMG")
      (.preventDefault event)
      (set-page
        {:img target
         :link parent}))))


(.addEventListener pages-container "click" on-click-page false)

(defn index-of
  [container child]
  (-> container
      (js/Array.from)
      (.indexOf child)))

(defn prev-comic
  []
  (let [selected (query-selector pages-container ".selected")
        prev (.-previousSibling selected)
        img  (query-selector prev "img")
        #_#_idx  (index-of pages-container prev)]
      (set-page
        {:img img
         :link prev})))

(defn toggle-nav
  []
  (let [selected (query-selector pages-container ".selected")
        prev (.-previousSibling selected)
        prev-link (get-by-id "prev-comic")
        next (.-nextSibling selected)
        next-link (get-by-id "next-comic")]
    (if prev
      (.. prev-link -classList (remove "hidden"))
      (.. prev-link -classList (add "hidden")))
    (if next
      (.. next-link -classList (remove "hidden"))
      (.. next-link -classList (add "hidden")))))

(defn next-comic
  []
  (let [selected (query-selector pages-container ".selected")
        next (.-nextSibling selected)
        img  (query-selector next "img")]
    (when next
      (set-page
        {:img img
         :link next}))))

(defn on-click-nav
  [event]
  (let [target (.. event -target)
        href (.-href target)
        id   (.-id target)]
    (js/console.log target href)
    (when (= (.-tagName target) "A")
      (.preventDefault event)
      (if (= id "prev-comic")
        (prev-comic)
        (next-comic))
      (toggle-nav))))


(def comic-ui (get-by-id "comic-ui"))

(.addEventListener comic-ui "click" on-click-nav false)


(js/console.log "pages-container" pages-container)

