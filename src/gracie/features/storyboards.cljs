(ns gracie.features.storyboards
  (:require
   [clojure.pprint :refer [pprint]]
   [clojure.string :as s]
   [promesa.core :as p]
   [framework.assets :refer [download fetch-image url->path]]
   [gracie.queue :as q]
   [gracie.data-pipeline :refer [defhook]]
   [notion.api :refer [fetch-blocks]]
   [notion.hiccup :refer [blocks->hiccup]]
   ["path" :as path]))

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
     :order            (get original-project :order)
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

(defn fetch-youtube-oembed
  [project url]
  (let [yt-api-url (str "https://youtube.com/oembed?url="
                        (js/encodeURIComponent url)
                        "&width=1280&height=720&format=json")
        params {:headers {"Referer"
                          "https://gracieanimator.squarespace.com"}}
        request (js/fetch yt-api-url (clj->js params))]
    (p/catch
     (p/-> request
           (.json)
           (js->clj :keywordize-keys true)
           (assoc :url url))
     (fn [error]
       (js/console.warn "Failed to fetch youtube url" url " for storyboard" (:title project))
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

(defn fetch-pdf
  [project url]
  (p/catch
   (p/let [name (.basename path (url->path url))
           local-url (download
                      {:url  url
                       :directory "pdfs"
                       :name name})]
     {:name name
      :url local-url})
   (fn [error]
     (js/console.warn "Failed to fetch pdf url" url "for storyboard" (:title project))
     (js/console.error error)
     {})))

(defn get-vimeo-url
  [project]
  (when-let [vimeo-url (:vimeo-url project)]
    (when (s/includes? vimeo-url "vimeo.com")
      vimeo-url)))

(defn get-youtube-url
  [project]
  (when-let [yt-url (:vimeo-url project)]
    (when (s/includes? yt-url "youtube.com")
      yt-url)))

(defhook :storyboards :queue-requests
  (fn storyboards-queue-requests
    [project]
    (concat
     []
     (when-let [block-id (:block-id project)]
       [{:id (str "notion/blocks/" block-id)
         :fetch #(p/-> (fetch-blocks {:block-id block-id})
                       (blocks->hiccup))
         :reducer #(assoc %1 :content %2)}])
     (when-let [vimeo-url (get-vimeo-url project)]
       [{:id vimeo-url
         :fetch #(fetch-vimeo-oembed project vimeo-url)
         :reducer #(assoc %1 :vimeo %2)}])
     (when-let [yt-url (get-youtube-url project)]
       [{:id yt-url
         :fetch #(fetch-youtube-oembed project yt-url)
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
  (when-let [thumbnail-url (some identity candidates)]
    (fetch-image project "storyboards" thumbnail-url)))

(defhook :storyboards :format-project
  (fn storyboards-format-project
    [{:keys [project responses]}]
    (let [{:keys [content vimeo speakerdecks pdfs]} responses]
      (p/let [thumbnail (download-thumbnail
                         project
                         [(:thumbnail-url project)
                          (:thumbnail_url vimeo)])]
        (merge project
               {:thumbnail thumbnail
                :content   content}
               (when vimeo
                 {:vimeo vimeo})
               (when (seq speakerdecks)
                 {:speakerdecks speakerdecks})
               (when pdfs
                 {:pdfs pdfs}))))))

