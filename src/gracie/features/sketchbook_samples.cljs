(ns gracie.features.sketchbook-samples
 (:require
  [promesa.core :as p]
  [gracie.data-pipeline :refer [defhook]]
  ["path" :as path]
  ["stream" :refer [Readable]]
  ["fs" :as fs]))

(defhook :sketchbook-samples :parse-project
 (fn sketchbook-samples-parse-project
  [original-project]
  {:id               (get original-project :id)
   :slug             (get original-project :slug)
   :title            (get original-project :title)
   :type             (get original-project :type)
   :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
   :published        (= (get-in original-project [:properties :published :checkbox]) true)
   :image-url        (get-in original-project [:properties :image :files 0 :file :url])}))


(defn url->path
  [url-str]
  (let [url (js/URL. url-str)]
   (.-pathname url)))

(defn download-asset
  [request {:keys [name url directory]}]
  (let [basename (str name (.extname path (url->path url)))
        target-dir (.resolve path (js/process.cwd) (.join path "public" "assets" directory))
        body (.-body request)
        file-path (.join path target-dir basename)
        url-path (.join path "/assets" directory basename)]
   (.mkdirSync fs target-dir #js {:recursive true})
   (-> (.fromWeb Readable body)
       (.pipe (fs/createWriteStream file-path)))
   url-path))

(defn fetch-image
  [project url]
  (p/catch
    (p/-> (js/fetch url)
          (download-asset
           {:url  url
            :directory "sketchbook-samples"
            :name (:slug project)}))
    (fn [error]
      (js/console.warn "Failed to fetch image url" url "for storyboard" (:title project))
      (js/console.error error)
      {})))


(defhook :sketchbook-samples :queue-requests
 (fn sketchbook-samples-queue-requests
   [project]
   [{:id (:image-url project)
     :fetch #(fetch-image project (:image-url project))
     :reducer #(assoc %1 :image-url %2)}]))

(defhook :sketchbook-samples :format-project
 (fn sketchbook-samples-format-project
  [{:keys [project responses]}]
  (let [{:keys [image-url]} responses]
   (assoc project
          :image-url image-url
          :thumbnail image-url))))
