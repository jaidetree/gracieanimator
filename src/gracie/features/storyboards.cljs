(ns gracie.features.storyboards
  (:require
    [clojure.pprint :refer [pprint]]
    [promesa.core :as p]
    [gracie.queue :as q]
    [gracie.data-pipeline :refer [defhook]]
    [notion.api :refer [fetch-blocks]]
    [framework.utils :as u]
    ["path" :as path]
    ["stream" :refer [Readable]]
    ["fs" :as fs]))

(defhook :storyboards :parse-project
  (fn storyboards-parse-project
    [original-project]
    {:id               (get original-project :id)
     :block-id         (get original-project :block-id)
     :slug             (get original-project :slug)
     :title            (get original-project :title)
     :type             (get original-project :type)
     :featured         (= (get-in original-project [:properties :featured :checkbox]) true)
     :published        (= (get-in original-project [:properties :published :checkbox]) true)
     :category         (get-in original-project [:properties :category :select :name])
     :vimeo-url        (get-in original-project [:properties :vimeo-url :url])
     :thumbnail-url    (get-in original-project [:properties :thumbnail :files 0 :file :url])
     :speakerdeck-urls (->> (get-in original-project [:properties :speakerdeck-url :files])
                            (map #(get-in % [:external :url])))
     :pdf-urls         (->> (get-in original-project [:properties :pdf :files])
                            (map #(get-in % [:file :url])))}))


(defn fetch-vimeo-oembed
  [project url]
  (let [vimeo-api-url (str "https://vimeo.com/api/oembed.json?url="
                           (js/encodeURIComponent url)
                           "&width=1280&height=720")
        params {:headers {"Referer"
                          "https://gracieanimator.squarespace.com"}}
        request (js/fetch vimeo-api-url (clj->js params))]
    (p/catch
      (p/-> request
            (.json)
            (js->clj :keywordize-keys true)
            (update :thumbnail_url #(str % ".jpg"))
            (assoc :url url))
      (fn [error]
        (js/console.warn "Failed to fetch vimeo url" url " for storyboard" (:title project))
        (js/console.error error)
        {}))))

(defn fetch-speakerdeck-oembed
  [project url]
  (let [vimeo-api-url (str "https://speakerdeck.com/oembed.json?url="
                           (js/encodeURIComponent url))
        request (js/fetch vimeo-api-url)]
    (p/catch
      (p/-> request
            (.json)
            (js->clj :keywordize-keys true)
            (assoc :url url))
      (fn [error]
        (js/console.warn "Failed to fetch speakerdeck url" vimeo-api-url "for storyboard" (:title project))
        (js/console.error error)
        {}))))

(defn url->path
  [url-str]
  (let [url (js/URL. url-str)]
   (.-pathname url)))

(defn download-asset
  [request {:keys [name url directory]}]
  (let [extname (.extname path (url->path url))
        basename (str (.basename path name extname) extname)
        target-dir (.resolve path (js/process.cwd) (.join path "public" "assets" directory))
        body (.-body request)
        file-path (.join path target-dir basename)
        url-path (.join path "/assets" directory basename)]
   (.mkdirSync fs target-dir #js {:recursive true})
   (-> (.fromWeb Readable body)
       (.pipe (fs/createWriteStream file-path)))
   url-path))

(defn fetch-image
  [project image-type url]
  (p/catch
    (p/-> (js/fetch url)
          (download-asset
           {:url  url
            :directory image-type
            :name (:slug project)}))
    (fn [error]
      (js/console.warn "Failed to fetch image url" url "for storyboard" (:title project))
      (js/console.error error)
      {})))

(defn fetch-pdf
  [project url]
  (p/catch
    (p/let [name (.basename path (url->path url))
            pdf-url (p/-> (js/fetch url)
                         (download-asset
                          {:url  url
                           :directory "pdfs"
                           :name name}))]
      {:name name
       :url  pdf-url})
    (fn [error]
      (js/console.warn "Failed to fetch pdf url" url "for storyboard" (:title project))
      (js/console.error error)
      {})))

(defhook :storyboards :queue-requests
  (fn storyboards-queue-requests
    [project]
    (concat
      []
      (when-let [block-id (:block-id project)]
        [{:id (str "notion/blocks/" block-id)
          :fetch #(fetch-blocks {:block-id block-id})
          :reducer #(assoc %1 :blocks %2)}])
      (when-let [vimeo-url (:vimeo-url project)]
        [{:id vimeo-url
          :fetch #(fetch-vimeo-oembed project vimeo-url)
          :reducer #(assoc %1 :vimeo %2)}])
      (when-let [speakerdeck-urls (seq (:speakerdeck-urls project))]
        (for [speakerdeck-url speakerdeck-urls]
          {:id speakerdeck-url
           :fetch #(fetch-speakerdeck-oembed project speakerdeck-url)
           :reducer #(update %1 :speakerdecks conj %2)}))
      (when-let [pdf-urls (seq (:pdf-urls project))]
       (for [pdf-url pdf-urls]
        {:id pdf-url
         :fetch #(fetch-pdf project pdf-url)
         :reducer #(update %1 :pdfs conj %2)}))
      #_(when-let [thumbnail-url (:thumbnail-url project)]
          [{:id thumbnail-url
            :fetch #(fetch-image project "thumbnails" thumbnail-url)
            :reducer #(assoc %1 :thumbnail %2)}]))))

(defn download-thumbnail
  [project candidates]
  (when-let [thumbnail-url (->> candidates
                                (filter identity)
                                (first))]
    (q/enqueue
      {:type :resource
       :requests [{:id thumbnail-url
                   :fetch #(fetch-image project "thumbnails" thumbnail-url)
                   :reducer (fn [_ctx local-thumbnail-url]
                              local-thumbnail-url)}]})))


(defhook :storyboards :format-project
  (fn storyboards-format-project
    [{:keys [project responses]}]
    (let [{:keys [blocks vimeo speakerdecks pdfs]} responses]
      (p/let [thumbnail (download-thumbnail
                          project
                          [(:thumbnail-url project)
                           (:thumbnail_url vimeo)])]
           (merge project
                  {:thumbnail thumbnail
                   :blocks    blocks}
                  (when vimeo
                   {:vimeo vimeo})
                  (when (seq speakerdecks)
                    {:speakerdecks speakerdecks})
                  (when pdfs
                   {:pdfs pdfs}))))))

