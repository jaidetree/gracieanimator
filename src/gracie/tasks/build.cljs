(ns gracie.tasks.build
  (:require
   [clojure.pprint :refer [pprint]]
   [promesa.core :as p]
   [framework.env :as env]
   [framework.utils :as u]
   [framework.assets :as assets]
   [gracie.projects.core :as projects]
   [notion.api :as notion]
   [gracie.views.base :refer [base]]
   [reagent.dom.server :as rdom]
   ["path" :as path]
   ["fs" :as fs]
   [gracie.routes.index :as home]
   [gracie.routes.storyboards.index :as storyboards]
   [gracie.routes.storyboards.category.$category-slug :as category]
   [gracie.routes.storyboards.$storyboard-id.$storyboard-slug :as storyboard]
   [gracie.routes.illustrations :as illustrations]
   [gracie.routes.sketchbook-samples :as sketchbook]
   [gracie.routes.comics :as comics]
   [gracie.routes.$page-slug :as dynamic-page]
   ))

(assets/set-basedir! "build")

(defn fetch-projects
  []
  (p/->> (notion/fetch-db-entries
          {:db-id (env/required "CMS_STORYBOARDS_ID")
           :filter {:and [{:property "Published"
                           :checkbox {:equals true}}]}})
         (projects/format-projects)
         (projects/sort-newest-first)))



(def build-dir (.resolve path (js/process.cwd) "build"))

(defn write-file
  [filename contents]
  (let [filepath (.join path build-dir filename)]
    (println "Writing" filename)
    (.mkdirSync fs (.dirname path filepath) #js {:recursive true})
    (u/write-file filepath contents)))

(defn write-hiccup
  [filename hiccup-vec]
  (write-file filename (rdom/render-to-static-markup hiccup-vec)))

(defn group-by-type
  [projects]
  (p/->> projects
         (projects/group-by-type)
         (projects/sort-types)))

(defn build-home
  [{:keys [projects pages]}]
  (p/let [projects-by-type (->> projects
                                (filter :featured)
                                (group-by-type))]
      (let [data {:projects-by-type projects-by-type
                  :pages            pages}
            req (merge {} {:data data})]
        (write-hiccup "index.html" (base req data (home/view req data))))))

(defn build-storyboards
  [{:keys [projects pages]}]
  (p/let [categories (p/->> projects
                            (filter #(= (:type %) "Storyboards"))
                            (projects/group-by-category))]
    (let [data {:pages      pages
                :categories categories}
          req (merge {} {:data data})]
      (write-hiccup "storyboards/index.html" (base req data (storyboards/view req data)))
      )))

(defn build-storyboard-categories
  [{:keys [projects pages]}]
  (p/let [categories (p/->> projects
                            (filter #(= (:type %) "Storyboards"))
                            (projects/group-by-category))]
    (for [[category storyboards] categories]
      (let [data {:pages       pages
                  :category    category
                  :storyboards storyboards
                  :categories  categories}
            slug (u/slugify category)
            req (merge {} {:data data})]
        (write-hiccup
         (str "storyboards/category/" slug "/index.html")
         (base req data (category/view req data)))
        ))))

(defn build-storyboard-pages
  [{:keys [projects pages]}]
  (p/let [storyboards (p/->> projects
                             (filter #(= (:type %) "Storyboards")))]
    (p/all
     (for [storyboard storyboards]
       (p/let [blocks (notion/fetch-all-blocks {:block-id (:id storyboard)})]
         (let [slug (u/slugify (:title storyboard))
               id   (u/uid->base64 (:uid storyboard))
               data {:pages       pages
                     :storyboard  storyboard
                     :id id
                     :slug slug
                     :blocks blocks}
               req (merge {} {:data data})]
           (write-hiccup
            (str "storyboards/" id "/" slug ".html")
            (base req data (storyboard/view req data)))
           ))))))

(defn build-illustrations
  [{:keys [projects pages]}]
  (p/let [illustrations (p/->> projects
                               (filter #(= (:type %) "Illustrations")))]
    (let [data {:pages      pages
                :illustrations illustrations}
          req (merge {} {:data data})]
      (write-hiccup
       "illustrations/index.html"
       (base req data (illustrations/view req data)))
      )))

(defn build-sketches
  [{:keys [projects pages]}]
  (p/let [images (p/->> projects
                               (filter #(= (:type %) "Sketchbook Samples")))]
    (let [data {:pages      pages
                :images images}
          req (merge {} {:data data})]
      (write-hiccup
       "sketchbook-samples/index.html"
       (base req data (sketchbook/view req data)))
      )))

(defn build-comics
  [{:keys [projects pages]}]
  (p/let [images (p/->> projects
                               (filter #(= (:type %) "Comics")))]
    (let [data {:pages      pages
                :images images}
          req (merge {} {:data data})]
      (write-hiccup
       "comics/index.html"
       (base req data (comics/view req data)))
      )))

(defn build-dynamic-pages
  [{:keys [pages]}]
  (p/all
   (for [page pages]
     (p/let [blocks (notion/fetch-all-blocks {:block-id (:id page)})]
       (let [slug (:slug page)
             data {:page       page
                   :pages      pages
                   :blocks     blocks}
             req (merge {} {:data data})]
         (write-hiccup
          (str slug ".html")
          (base req data (dynamic-page/view req data)))
         )))))


(defn -main
  [& args]
  (let [req {}]
    (p/let [[projects pages] (p/all [(fetch-projects)
                                     (projects/fetch-pages)])]
      (p/do
        (build-home
         {:projects projects
          :pages    pages})

        (build-storyboards
         {:projects projects
          :pages    pages})

        (build-storyboard-categories
         {:projects projects
          :pages    pages})

        (build-storyboard-pages
         {:projects projects
          :pages    pages})

        (build-illustrations
         {:projects projects
          :pages    pages})

        (build-sketches
         {:projects projects
          :pages    pages})

        (build-comics
         {:projects projects
          :pages    pages})

        (build-dynamic-pages
         {:pages    pages})

        (println "Site built")))))
